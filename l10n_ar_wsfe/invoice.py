# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2013 E-MIPS (http://www.e-mips.com.ar) All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
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

from openerp.osv import osv
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import models, fields, api, _
from datetime import datetime
from openerp import pooler
import time
import re

__author__ = "Sebastian Kennedy <skennedy@e-mips.com.ar>"


class account_invoice(models.Model):
    _name = "account.invoice"
    _inherit = "account.invoice"

    aut_cae = fields.Boolean('Autorizar', default=False, help='Pedido de autorizacion a la AFIP')
    cae = fields.Char('CAE/CAI', size=32, required=False, help='CAE (Codigo de Autorizacion Electronico assigned by AFIP.)')
    cae_due_date = fields.Date('CAE Due Date', required=False, help='Fecha de vencimiento del CAE')
    #'associated_inv_ids': fields.many2many('account.invoice', )
    associated_inv_ids = fields.Many2many('account.invoice', 'account_invoice_associated_rel', 'invoice_id', 'refund_debit_id')

    # Campos para facturas de exportacion. Aca ninguno es requerido,
    # eso lo hacemos en la vista ya que depende de si es o no factura de exportacion
    export_type_id = fields.Many2one('wsfex.export_type.codes', 'Export Type')
    dst_country_id = fields.Many2one('wsfex.dst_country.codes', 'Dest Country')
    dst_cuit_id = fields.Many2one('wsfex.dst_cuit.codes', 'Country CUIT')
    shipping_perm_ids = fields.One2many('wsfex.shipping.permission', 'invoice_id', 'Shipping Permissions')
    incoterm_id = fields.Many2one('stock.incoterms', 'Incoterm', help="International Commercial Terms are a series of predefined commercial terms used in international transactions.")
    wsfe_request_ids = fields.One2many('wsfe.request.detail', 'name')
    wsfex_request_ids = fields.One2many('wsfex.request.detail', 'invoice_id')

    @api.multi
    def onchange_partner_id(self, type, partner_id, date_invoice=False,
            payment_term=False, partner_bank_id=False, company_id=False):

        res = super(account_invoice, self).onchange_partner_id(type, partner_id,\
                    date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False)

        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            country_id = partner.country_id.id or False
            if country_id:
                dst_country = self.env['wsfex.dst_country.codes'].search([('country_id','=',country_id)])

                if dst_country:
                    res['value'].update({'dst_country_id': dst_country[0].id})
        return res

    # Esto lo hacemos porque al hacer una nota de credito, no le setea la fiscal_position
    # Ademas, seteamos el comprobante asociado
    def refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None, context=None):
        new_ids = super(account_invoice, self).refund(cr, uid, ids, date, period_id, description, journal_id, context=context)

        for refund_id in new_ids:
            vals = {}
            refund = self.browse(cr, uid, refund_id)
            invoice = self.browse(cr, uid, ids[0])
            if not refund.fiscal_position:
                fiscal_position = refund.partner_id.property_account_position
                vals = {'fiscal_position': fiscal_position.id}

            if not invoice.local:
                vals['export_type_id'] = invoice.export_type_id.id
                vals['dst_country_id'] = invoice.dst_country_id.id
                vals['dst_cuit_id'] = invoice.dst_cuit_id.id
                vals['associated_inv_ids'] = [(4, invoice.id)]

            # Agregamos el comprobante asociado y otros campos necesarios
            if vals:
                self.write(cr, uid, refund_id, vals)
        return new_ids

    @api.model
    def _check_fiscal_values(self):
        self.ensure_one()
        inv = self
        # Si es factura de cliente
        denomination_id = inv.denomination_id and inv.denomination_id.id or False
        if inv.type in ('out_invoice', 'out_refund'):

            if not denomination_id:
                raise except_orm(_('Error!'), _('Denomination not set in invoice'))

            if inv.pos_ar_id.denomination_id.id != denomination_id:
                raise except_orm(_('Error!'), _('Point of sale has not the same denomination as the invoice.'))

            # Chequeamos que la posicion fiscal y la denomination_id coincidan
            if inv.fiscal_position.denomination_id.id != denomination_id:
                raise except_orm(_('Error'),
                                     _('The invoice denomination does not corresponds with this fiscal position.'))

        # Si es factura de proveedor
        else:
            if not denomination_id:
                raise except_orm(_('Error!'), _('Denomination not set in invoice'))

            # Chequeamos que la posicion fiscal y la denomination_id coincidan
            if inv.fiscal_position.denom_supplier_id.id != inv.denomination_id.id:
                raise except_orm(_('Error'),
                                     _('The invoice denomination does not corresponds with this fiscal position.'))

        # Chequeamos que la posicion fiscal de la factura y del cliente tambien coincidan
        if inv.fiscal_position.id != inv.partner_id.property_account_position.id:
            raise except_orm(_('Error'),
                                 _('The invoice fiscal position is not the same as the partner\'s fiscal position.'))

        return True

    @api.multi
    def _get_next_wsfe_number(self, conf):
        self.ensure_one()
        inv = self
        voucher_type_obj = self.env['wsfe.voucher_type']

        # Obtenemos el tipo de comprobante
        tipo_cbte = voucher_type_obj.get_voucher_type(inv)
        try:
            pto_vta = int(inv.pos_ar_id.name)
        except ValueError:
            raise except_orm('Error', 'El nombre del punto de venta tiene que ser numerico')

        res = conf.get_last_voucher(pto_vta, tipo_cbte)

        return res + 1

    @api.multi
    def get_next_invoice_number(self):
        """Funcion para obtener el siguiente numero de comprobante correspondiente en el sistema"""
        self.ensure_one()
        invoice = self
        cr = self.env.cr
        # Obtenemos el ultimo numero de comprobante para ese pos y ese tipo de comprobante
        cr.execute("select max(to_number(substring(internal_number from '[0-9]{8}$'), '99999999')) from account_invoice where internal_number ~ '^[0-9]{4}-[0-9]{8}$' and pos_ar_id=%s and state in %s and type=%s and is_debit_note=%s", (invoice.pos_ar_id.id, ('open', 'paid', 'cancel',), invoice.type, invoice.is_debit_note))
        last_number = cr.fetchone()
        self.env.invalidate_all()

        # Si no devuelve resultados, es porque es el primero
        if not last_number or not last_number[0]:
            next_number = 1
        else:
            next_number = last_number[0] + 1

        return next_number

    # Heredado para no cancelar si es una factura electronica
    # TODO: Migrar a v8
    def action_cancel(self, cr, uid, ids, context=None):

        invoices = self.read(cr, uid, ids, ['aut_cae'])
        for i in invoices:
            if i['aut_cae']:
                raise osv.except_osv(_("Electronic Invoice Error!"), _("You cannot cancel an Electronic Invoice because it has been informed to AFIP."))

        return super(account_invoice, self).action_cancel(cr, uid, ids, context=context)

    @api.multi
    def action_number(self):
        wsfe_conf_obj = self.env['wsfe.config']
        wsfex_conf_obj = self.env['wsfex.config']
        wsfe_conf = wsfe_conf_obj.get_config()
        wsfex_conf = wsfex_conf_obj.get_config()

        next_number = None
        invoice_vals = {}
        invtype = None

        # TODO: not correct fix but required a fresh values before reading it.
        # Esto se usa para forzar a que recalcule los campos funcion
        self.write({})

        for obj_inv in self:
            invtype = obj_inv.type

            # Chequeamos si es local por medio de la posicion fiscal
            local = True
            local = obj_inv.fiscal_position.local

            reference = obj_inv.reference or ''

            # Si es local o de cliente
            if local or invtype in ('out_invoice', 'out_refund'):
                # Chequeamos los valores fiscales
                self._check_fiscal_values()

            # si el usuario no ingreso un numero, busco el ultimo y lo incremento , si no hay ultimo va 1.
            # si el usuario hizo un ingreso dejo ese numero
            internal_number = obj_inv.internal_number
            next_number = False

            # Si son de Cliente
            if invtype in ('out_invoice', 'out_refund'):

                pos_ar = obj_inv.pos_ar_id
                next_number = self.get_next_invoice_number()

                # Chequeamos si corresponde Factura Electronica
                # Aca nos fijamos si el pos_ar_id tiene factura electronica asignada
                confs = filter(lambda c: pos_ar in c.point_of_sale_ids, [wsfe_conf, wsfex_conf]) #_get_ws_conf(obj_inv.pos_ar_id)

                if len(confs)>1:
                    raise osv.except_osv(_("WSFE Error"), _("There is more than one configuration with this POS %s") % pos_ar.name)

                if confs:
                    conf = confs[0]
                    invoice_vals['aut_cae'] = True
                    fe_next_number = obj_inv._get_next_wsfe_number(conf)

                    # Si es homologacion, no hacemos el chequeo del numero
                    if not conf.homologation:
                        if fe_next_number != next_number:
                            raise except_orm(_("WSFE Error!"), _("The next number [%d] does not corresponds to that obtained from AFIP WSFE [%d]") % (int(next_number), int(fe_next_number)))
                    else:
                        next_number = fe_next_number

                # Si no es Factura Electronica...
                else:
                    # Nos fijamos si el usuario dejo en blanco el campo de numero de factura
                    if obj_inv.internal_number:
                        internal_number = obj_inv.internal_number

                # Lo ponemos como en Proveedores, o sea, A0001-00000001
                if not internal_number:
                    internal_number = '%s-%08d' % (pos_ar.name, next_number)

                m = re.match('^[0-9]{4}-[0-9]{8}$', internal_number)
                if not m:
                    raise except_orm(_('Error'), _('The Invoice Number should be the format XXXX-XXXXXXXX'))

                # Escribimos el internal number
                invoice_vals['internal_number'] = internal_number

            # Si son de Proveedor
            else:
                if not obj_inv.internal_number:
                    raise except_orm(_('Error'), _('The Invoice Number should be filled'))

                if local:
                    m = re.match('^[0-9]{4}-[0-9]{8}$', obj_inv.internal_number)
                    if not m:
                        raise except_orm(_('Error'), _('The Invoice Number should be the format XXXX-XXXXXXXX'))

            # Escribimos los campos necesarios de la factura
            obj_inv.write(invoice_vals)

            invoice_name = obj_inv.name_get()[0][1]
            if not reference:
                ref = invoice_name
            else:
                ref = '%s [%s]' % (invoice_name, reference)

            # Actulizamos el campo reference del move_id correspondiente a la creacion de la factura
            obj_inv._update_reference(ref)

        return True

#    def wsfe_invoice_prepare_detail(self, cr, uid, ids, conf, context=None):
#        conf_obj = conf._model
#
#        details = conf_obj.prepare_details(cr, uid, conf, ids, context=context)
#        return details

    @api.model
    def hook_add_taxes(self, inv, detalle):
        return detalle

    @api.multi
    def action_aut_cae(self):
        voucher_type_obj = self.env['wsfe.voucher_type']

        wsfe_conf_obj = self.env['wsfe.config']
        wsfe_conf = wsfe_conf_obj.get_config()

        wsfex_conf_obj = self.env['wsfex.config']
        wsfex_conf = wsfex_conf_obj.get_config()

        for inv in self:
            if not inv.aut_cae:
                #self.write(cr, uid, ids, {'cae' : 'NA'})
                return True

            pos_ar = inv.pos_ar_id
            # Chequeamos si corresponde Factura Electronica
            # Aca nos fijamos si el pos_ar_id tiene factura electronica asignada
            confs = filter(lambda c: pos_ar in c.point_of_sale_ids, [wsfe_conf, wsfex_conf]) #_get_ws_conf(obj_inv.pos_ar_id)

            if len(confs)>1:
                raise osv.except_osv(_("WSFE Error"), _("There is more than one configuration with this POS %s") % pos_ar.name)

            if confs:
                conf = confs[0]
            else:
                raise osv.except_osv(_("WSFE Error"), _("There is no configuration for this POS %s") % pos_ar.name)

            # Obtenemos el tipo de comprobante
            tipo_cbte = voucher_type_obj.get_voucher_type(inv)

            # Obtenemos el numero de comprobante a enviar a la AFIP teniendo en
            # cuenta que inv.number == 000X-00000NN o algo similar.
            # TODO: Esto esta duplicado en los metodos de wsfe y wsfex
            inv_number = inv.internal_number
            pos, cbte_nro = inv_number.split('-')
            pos = int(pos)
            cbte_nro = int(cbte_nro)

            # Derivamos a la configuracion correspondiente
            fe_det_req = conf.prepare_details([inv])
            result = conf.get_invoice_CAE(pos, tipo_cbte, fe_det_req)

            new_cr = False
            try:
                invoices_approbed = conf._parse_result([inv], result)

                for invoice_id, invoice_vals in invoices_approbed.iteritems():
                    inv_obj = self.env['account.invoice'].browse(invoice_id)
                    inv_obj.write(invoice_vals)
            except Exception as e:
                new_cr = self.env.cr.dbname
                self.env.cr.rollback()
                raise e
            finally:
                # Creamos el wsfe.request con otro cursor, porque puede pasar que
                # tengamos una excepcion e igualmente, tenemos que escribir la request
                # Sino al hacer el rollback se pierde hasta el wsfe.request
                if new_cr:
                    cr2 = pooler.get_db(new_cr).cursor()
                else:
                    cr2 = self.env.cr

                new_env = conf.env(cr=cr2)
                conf.with_env(new_env)._log_wsfe_request(pos, tipo_cbte, fe_det_req, result)
                if new_cr:
                    cr2.commit()
                    cr2.close()
        return True

    @api.multi
    def _parse_result(self, result):
        invoices_approbed = {}

        # Verificamos el resultado de la Operacion
        # Si no fue aprobado
        if result['Resultado'] == 'R':
            msg = ''
            if result['Errores']:
                msg = 'Errores: ' + '\n'.join(result['Errores']) + '\n'

            if self._context.get('raise-exception', True):
                raise except_orm(_('AFIP Web Service Error'),
                                     _('La factura no fue aprobada. \n%s') % msg)

        elif result['Resultado'] == 'A' or result['Resultado'] == 'P':
            index = 0
            for inv in self:
                invoice_vals = {}
                comp = result['Comprobantes'][index]
                if comp['Observaciones']:
                    msg = 'Observaciones: ' + '\n'.join(comp['Observaciones'])

                    # Escribimos en el log del cliente web
                    #self.log(cr, uid, inv.id, msg, context)

                # Si es un contacto, tomamos el partner que es el que tiene la informacion contable
                partner_id = inv.partner_id.parent_id and inv.partner_id.parent_id or inv.partner_id

                # Chequeamos que se corresponda con la factura que enviamos a validar
                doc_type = partner_id.document_type_id and partner_id.document_type_id.afip_code or '99'
                doc_tipo = comp['DocTipo'] == int(doc_type)
                doc_num = comp['DocNro'] == int(partner_id.vat)
                cbte = True
                if inv.internal_number:
                    cbte = comp['CbteHasta'] == int(inv.internal_number.split('-')[1])
                else:
                    # TODO: El nro de factura deberia unificarse para que se setee en una funcion
                    # o algo asi para que no haya posibilidad de que sea diferente nunca en su formato
                    invoice_vals['internal_number'] = '%04d-%08d' % (result['PtoVta'], comp['CbteHasta'])

                if not all([doc_tipo, doc_num, cbte]):
                    raise except_orm(_("WSFE Error!"), _("Validated invoice that not corresponds!"))

                if comp['Resultado'] == 'A':
                    invoice_vals['cae'] = comp['CAE']
                    invoice_vals['cae_due_date'] = comp['CAEFchVto']
                    invoices_approbed[inv.id] = invoice_vals
                    #self.write(cr, uid, inv.id, invoice_vals)
                    # invoices_approbed.append(inv.id)

                index += 1

        return invoices_approbed

    @api.one
    def wsfe_relate_invoice(self, pos, number, date_invoice, cae, cae_due_date):
        # Tomamos la factura y mandamos a realizar
        # el asiento contable primero.
        self.action_move_create()

        invoice_vals = {
            'internal_number': '%04d-%08d' % (pos, number),
            'date_invoice': date_invoice,
            'cae': cae,
            'cae_due_date': cae_due_date,
        }

        # Escribimos los campos necesarios de la factura
        self.write(invoice_vals)

        invoice_name = self.name_get()[0][1]
        if not self.reference:
            ref = invoice_name
        else:
            ref = '%s [%s]' % (invoice_name, self.reference)

        # Actulizamos el campo reference del move_id correspondiente a la creacion de la factura
        self._update_reference(ref)

        # Llamamos al workflow para que siga su curso
        self.signal_workflow('invoice_massive_open')
        return

account_invoice()


class account_invoice_tax(models.Model):
    _name = "account.invoice.tax"
    _inherit = "account.invoice.tax"

    @api.multi
    def hook_compute_invoice_taxes(self, invoice, tax_grouped):
        tax_obj = self.env['account.tax']
        currency = invoice.currency_id.with_context(date=invoice.date_invoice or fields.Date.context_today(invoice))

        for t in tax_grouped.values():
            # Para solucionar el problema del redondeo con AFIP
            ta = tax_obj.browse(t['tax_id'])
            t['amount'] = t['base'] * ta.amount
            t['tax_amount'] = t['base_amount'] * ta.amount

            t['base'] = currency.round(t['base'])
            t['amount'] = currency.round(t['amount'])
            t['base_amount'] = currency.round(t['base_amount'])
            t['tax_amount'] = currency.round(t['tax_amount'])

        return super(account_invoice_tax, self).hook_compute_invoice_taxes(invoice, tax_grouped)

account_invoice_tax()
