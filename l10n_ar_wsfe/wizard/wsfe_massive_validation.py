##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
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

        invoices = inv_obj.browse(self.env.context['active_ids'])
        invoices = invoices.sorted(key=lambda x: x.create_date)

        company = invoices.mapped('pos_ar_id.company_id')
        company.ensure_one()
        conf = wsfe_conf_obj.with_context(company_id=company.id).get_config()

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
                _('WSFE Error!\n') +
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
                _('WSFE Error!\n') +
                _('You are trying to validate several invoices but not all ' +
                  'of them belongs to the same point of sale'))

        draft_state = map(lambda x: x.state == 'draft', invoices)

        # Estan todas en estado 'Draft'?
        if not all(draft_state):
            raise UserError(
                _('WSFE Error!\n') +
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
                _('WSFE Error!\n') +
                _("You are trying to validate several invoices but not all " +
                  "of them are the same type. For example, all Customer " +
                  "Invoices or all Customer Refund"))

        # Preparamos el lote de facturas para la AFIP
        next_system_number = invoices[0].get_next_invoice_number()

        no_create_move = self.env.context.get('no_create_move', False)
        if not no_create_move:
            for index, inv in enumerate(invoices):
                ctx = self.env.context.copy()
                ctx.update({
                    'invoice_number_offset': index,
                })
                inv.with_context(ctx).action_move_create()

        request_log = invoices._validate_electronic_invoices(
            first_number=next_system_number)

        return {
            'name': _('WSFE Request'),
            'res_id': request_log.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wsfe.request',
            'type': 'ir.actions.act_window',
        }
