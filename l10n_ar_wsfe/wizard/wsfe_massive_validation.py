# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2013 E-MIPS (http://www.e-mips.com.ar) All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General
#    Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import api, models, _
from odoo.exceptions import UserError


class AccountInvoiceConfirm(models.TransientModel):
    """
    This wizard will confirm the all the selected draft invoices
    """
    _name = "account.invoice.confirm"
    _inherit = "account.invoice.confirm"

    @api.multi
    def invoice_confirm(self):
        wsfe_conf_obj = self.env['wsfe.config']
        inv_obj = self.env['account.invoice']

        conf = wsfe_conf_obj.get_config()

        invoices = inv_obj.browse(self.env.context['active_ids'])

        # Primero tenemos que chequear si al menos alguna de las facturas
        # se debe hacer por factura electronica
        conf_electronic_pos = conf.point_of_sale_ids
        inv_electronic_pos = map(lambda x: x.pos_ar_id in conf_electronic_pos,
                                 invoices)

        # Si se estan validando facturas que ninguna pertenece a punto
        # de venta electronico, seguimos como siempre
        if not any(inv_electronic_pos):
            return super(AccountInvoiceConfirm, self).invoice_confirm()

        # Si estamos en este punto es porque alguna o todas es electronica
        if not all(inv_electronic_pos):
            raise UserError(
                _('WSFE Error!'),
                _('You are trying to validate several invoices but not all ' +
                  'of them belongs to an electronic point of sale'))

        # La condicion para que se pueda validar un lote de
        # facturas electronicas es que deben ser del mismo Punto de Venta,
        # el mismo Tipo de Comprobante y obviamente estar en estado 'Draft'
        pos_ids = invoices.mapped('pos_ar_id').ids
        same_pos = len(set(pos_ids)) == 1

        # Son todas del mismo Punto de Venta?
        if not same_pos:
            raise UserError(
                _('WSFE Error!'),
                _('You are trying to validate several invoices but not all ' +
                  'of them belongs to the same point of sale'))

        draft_state = map(lambda x: x.state == 'draft', invoices)

        # Estan todas en estado 'Draft'?
        if not all(draft_state):
            raise UserError(
                _('WSFE Error!'),
                _("You are trying to validate several invoices but not " +
                  "all of them are in 'draft' state"))

        v_types = []
        for inv in invoices:
            voucher_type = inv._get_voucher_type()
            v_types.append(voucher_type)

        same_type = len(set(v_types)) == 1

        # Son todas el mismo Tipo de Comprobante?
        if not same_type:
            raise UserError(
                _('WSFE Error!'),
                _("You are trying to validate several invoices but not all " +
                  "of them are the same type. For example, all Customer " +
                  "Invoices or all Customer Refund"))

        # Preparamos el lote de facturas para la AFIP
        next_system_number = invoices[0].get_next_invoice_number()

        # if not conf.homologation:
        #     if next_wsfe_number != next_system_number:
        #         raise UserError(
        #             _("WSFE Error!"),
        #             _("The next number in the system [%d] does not match " +
        #               "the one obtained from AFIP WSFE [%d]") %
        #             (int(next_system_number), int(next_wsfe_number)))

        no_create_move = self.env.context.get('no_create_move', False)
        if not no_create_move:
            for inv in invoices:
                inv.action_move_create()

        ws = invoices.new_ws(conf=conf)
        try:
            invoices_approved = ws.send_invoices(
                invoices, first_number=next_system_number)

            # Para las facturas aprobadas creo los asientos,
            # y seguimos adelante con el workflow
            for invoice_id, invoice_vals in invoices_approved.iteritems():
                invoice = inv_obj.browse(invoice_id)

                invoice.write(invoice_vals)

                if not no_create_move:
                    ref = invoice.reference or ''
                    if not ref:
                        invoice_name = self.name_get()[0][1]
                        ref = invoice_name
                    invoice._update_reference(ref)

                # Llamamos al workflow para que siga su curso
                invoice.signal_workflow('invoice_massive_open')
            self.env.cr.commit()
        except Exception as e:
            err = _('Error received was: \n %s') % e
            raise UserError(
                _('WSFE Validation Error'), err)
        finally:
            # Creamos el wsfe.request con otro cursor,
            # porque puede pasar que
            # tengamos una excepcion e igualmente,
            # tenemos que escribir la request
            # Sino al hacer el rollback se pierde hasta el wsfe.request
            self.env.cr.rollback()
            with api.Environment.manage():
                new_cr = self.env.cursor()
                new_env = api.Environment(new_cr, self.env.user.id,
                                          self.env.context)
                request_log = ws.log_request(new_env)
                new_cr.commit()
                new_cr.close()

        # TODO: Ver que pasa con las account_analytic_lines
        return {
            'name': _('WSFE Request'),
            'domain': "[('id','=',%s)]" % (request_log.id),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'wsfe.request',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
