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

from osv import osv, fields
from datetime import datetime
from tools.translate import _
import pooler
import time
import re

__author__ = "Sebastian Kennedy <skennedy@e-mips.com.ar>"

class account_invoice(osv.osv):
    _name = "account.invoice"
    _inherit = "account.invoice"

    _columns = {
        'aut_cae': fields.boolean('Autorizar', help='Pedido de autorizacion a la AFIP'),
        'cae': fields.char('CAE/CAI', size=32, required=False, help='CAE (Codigo de Autorizacion Electronico assigned by AFIP.)'),
        'cae_due_date': fields.date('CAE Due Date', required=False, help='Fecha de vencimiento del CAE'),
        'associated_inv_ids': fields.many2many('account.invoice', 'account_invoice_associated_rel', 'invoice_id', 'refund_debit_id'),
        # Campos para facturas de exportacion. Aca ninguno es requerido,
        # eso lo hacemos en la vista ya que depende de si es o no factura de exportacion
        'export_type_id': fields.many2one('wsfex.export_type.codes', 'Export Type'),
        'dst_country_id': fields.many2one('wsfex.dst_country.codes', 'Dest Country'),
        'dst_cuit_id': fields.many2one('wsfex.dst_cuit.codes', 'Country CUIT'),
        'shipping_perm_ids': fields.one2many('wsfex.shipping.permission', 'invoice_id', 'Shipping Permissions'),
        'incoterm_id': fields.many2one('stock.incoterms', 'Incoterm', help="International Commercial Terms are a series of predefined commercial terms used in international transactions."),
        'wsfe_request_ids': fields.one2many('wsfe.request.detail', 'name'),
        'wsfex_request_ids': fields.one2many('wsfex.request.detail', 'invoice_id'),
    }

    _defaults = {
        'aut_cae': lambda *a: False,
    }

    def onchange_partner_id(self, cr, uid, ids, type, partner_id,\
            date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False , context=None):
        res =   super(account_invoice, self).onchange_partner_id(cr, uid, ids, type, partner_id,\
                date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False)

        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            country_id = partner.country_id.id or False
            if country_id:
                dst_country = self.pool.get('wsfex.dst_country.codes').search(cr, uid, [('country_id','=',country_id)])

                if dst_country:
                    res['value'].update({'dst_country_id': dst_country[0]})
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
                vals = {'fiscal_position':fiscal_position.id}

            # Agregamos el comprobante asociado y otros campos necesarios
            # si es de exportacion
            if not invoice.local:
                vals['export_type_id'] = invoice.export_type_id.id
                vals['dst_country_id'] = invoice.dst_country_id.id
                vals['dst_cuit_id'] = invoice.dst_cuit_id.id

            vals['associated_inv_ids'] = [(4, invoice.id)]

            if vals:
                self.write(cr, uid, refund_id, vals)
        return new_ids

    def _check_fiscal_values(self, cr, uid, inv):
        # Si es factura de cliente
        denomination_id = inv.denomination_id and inv.denomination_id.id or False
        if inv.type in ('out_invoice', 'out_refund'):

            if not denomination_id:
                raise osv.except_osv(_('Error!'), _('Denomination not set in invoice'))

            if inv.pos_ar_id.denomination_id.id != denomination_id:
                raise osv.except_osv(_('Error!'), _('Point of sale has not the same denomination as the invoice.'))

            # Chequeamos que la posicion fiscal y la denomination_id coincidan
            if inv.fiscal_position.denomination_id.id != denomination_id:
                raise osv.except_osv( _('Error'),
                            _('The invoice denomination does not corresponds with this fiscal position.'))

        # Si es factura de proveedor
        else:
            if not denomination_id:
                raise osv.except_osv(_('Error!'), _('Denomination not set in invoice'))

            # Chequeamos que la posicion fiscal y la denomination_id coincidan
            if inv.fiscal_position.denom_supplier_id.id != inv.denomination_id.id:
                raise osv.except_osv( _('Error'),
                                    _('The invoice denomination does not corresponds with this fiscal position.'))

        # Chequeamos que la posicion fiscal de la factura y del cliente tambien coincidan
        if inv.fiscal_position.id != inv.partner_id.property_account_position.id:
            raise osv.except_osv( _('Error'),
                                _('The invoice fiscal position is not the same as the partner\'s fiscal position.'))

        return True

    def _get_next_wsfe_number(self, cr, uid, conf, inv, context=None):
        voucher_type_obj = self.pool.get('wsfe.voucher_type')
        conf_obj = conf._model

        # Obtenemos el tipo de comprobante
        tipo_cbte = voucher_type_obj.get_voucher_type(cr, uid, inv, context=context)
        try:
            pto_vta = int(inv.pos_ar_id.name)
        except ValueError:
            raise osv.except_osv('Error', 'El nombre del punto de venta tiene que ser numerico')

        res = conf_obj.get_last_voucher(cr, uid, [conf.id], pto_vta, tipo_cbte, context=context)
        return res+1

    def get_next_invoice_number(self, cr, uid, invoice, context=None):
        """Funcion para obtener el siguiente numero de comprobante correspondiente en el sistema"""

        # Obtenemos el ultimo numero de comprobante para ese pos y ese tipo de comprobante
        cr.execute("select max(to_number(substring(internal_number from '[0-9]{8}$'), '99999999')) from account_invoice where internal_number ~ '^[0-9]{4}-[0-9]{8}$' and pos_ar_id=%s and state in %s and type=%s and is_debit_note=%s", (invoice.pos_ar_id.id, ('open', 'paid', 'cancel',), invoice.type, invoice.is_debit_note))
        last_number = cr.fetchone()

        # Si no devuelve resultados, es porque es el primero
        if not last_number or not last_number[0]:
            next_number = 1
        else:
            next_number = last_number[0] + 1

        return next_number

    # Heredado para no cancelar si es una factura electronica
    def action_cancel(self, cr, uid, ids, context=None):

        invoices = self.read(cr, uid, ids, ['aut_cae'])
        for i in invoices:
            if i['aut_cae']:
                raise osv.except_osv(_("Electronic Invoice Error!"), _("You cannot cancel an Electronic Invoice because it has been informed to AFIP."))

        return super(account_invoice, self).action_cancel(cr, uid, ids, context=context)

    def action_number(self, cr, uid, ids, context=None):
        wsfe_conf_obj = self.pool.get('wsfe.config')
        wsfe_conf = wsfe_conf_obj.get_config(cr, uid)

        wsfex_conf_obj = self.pool.get('wsfex.config')
        wsfex_conf = wsfex_conf_obj.get_config(cr, uid)

        if not context:
            context = {}

        next_number = None
        invoice_vals = {}
        invtype = None

        #TODO: not correct fix but required a fresh values before reading it.
        # Esto se usa para forzar a que recalcule los campos funcion
        self.write(cr, uid, ids, {})

        for obj_inv in self.browse(cr, uid, ids, context=context):
            partner_country = obj_inv.partner_id.country_id and obj_inv.partner_id.country_id.id or False
            company_country = obj_inv.company_id.country_id and obj_inv.company_id.country_id.id or False

            id = obj_inv.id
            invtype = obj_inv.type

            # Chequeamos si es local por medio de la posicion fiscal
            local = True
            local = obj_inv.fiscal_position.local

            reference = obj_inv.reference or ''

            # Si es local o de cliente
            if local or invtype in ('out_invoice', 'out_refund'):
                # Chequeamos los valores fiscales
                self._check_fiscal_values(cr, uid, obj_inv)

            # si el usuario no ingreso un numero, busco el ultimo y lo incremento , si no hay ultimo va 1.
            # si el usuario hizo un ingreso dejo ese numero
            internal_number = obj_inv.internal_number #False
            next_number = False

            # Si son de Cliente
            if invtype in ('out_invoice', 'out_refund'):

                pos_ar = obj_inv.pos_ar_id
                next_number = self.get_next_invoice_number(cr, uid, obj_inv, context=context)

                # Chequeamos si corresponde Factura Electronica
                # Aca nos fijamos si el pos_ar_id tiene factura electronica asignada
                confs = filter(lambda c: pos_ar in c.point_of_sale_ids, [wsfe_conf, wsfex_conf]) #_get_ws_conf(obj_inv.pos_ar_id)

                if len(confs)>1:
                    raise osv.except_osv(_("WSFE Error"), _("There is more than one configuration with this POS %s") % pos_ar.name)

                if confs:
                    conf = confs[0]
                    invoice_vals['aut_cae'] = True
                    fe_next_number = self._get_next_wsfe_number(cr, uid, conf, obj_inv, context=context)

                    # Si es homologacion, no hacemos el chequeo del numero
                    if not conf.homologation:
                        if fe_next_number != next_number:
                            raise osv.except_osv(_("WSFE Error!"), _("The next number [%d] does not corresponds to that obtained from AFIP WSFE [%d]") % (int(next_number), int(fe_next_number)))
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
                    raise osv.except_osv( _('Error'), _('The Invoice Number should be the format XXXX-XXXXXXXX'))

                # Escribimos el internal number
                invoice_vals['internal_number'] = internal_number

            # Si son de Proveedor
            else:
                if not obj_inv.internal_number:
                    raise osv.except_osv( _('Error'), _('The Invoice Number should be filled'))

                if local:
                    m = re.match('^[0-9]{4}-[0-9]{8}$', obj_inv.internal_number)
                    if not m:
                        raise osv.except_osv( _('Error'), _('The Invoice Number should be the format XXXX-XXXXXXXX'))


            # Escribimos los campos necesarios de la factura
            self.write(cr, uid, obj_inv.id, invoice_vals)

            invoice_name = self.name_get(cr, uid, [obj_inv.id])[0][1]
            if not reference:
                ref = invoice_name
            else:
                ref = '%s [%s]' % (invoice_name, reference)

            # Actulizamos el campo reference del move_id correspondiente a la creacion de la factura
            self._update_reference(cr, uid, obj_inv, ref, context=context)

            # Como sacamos el post de action_move_create, lo tenemos que poner aqui
            # Lo sacamos para permitir la validacion por lote. Ver wizard account.invoice.confirm
            move_id = obj_inv.move_id and obj_inv.move_id.id or False
            self.pool.get('account.move').post(cr, uid, [move_id], context={'invoice':obj_inv})

#            for inv_id, name in self.name_get(cr, uid, [id], context=context):
#                ctx = context.copy()
#                if invtype in ('out_invoice', 'out_refund'):
#                    ctx = self.get_log_context(cr, uid, context=ctx)
#                message = _('Invoice ') + " '" + name + "' "+ _("is validated.")
#                self.log(cr, uid, inv_id, message, context=ctx)

        return True

#    def wsfe_invoice_prepare_detail(self, cr, uid, ids, conf, context=None):
#        conf_obj = conf._model
#
#        details = conf_obj.prepare_details(cr, uid, conf, ids, context=context)
#        return details


    def hook_add_taxes(self, cr, uid, inv, detalle):
        return detalle

    def action_aut_cae(self, cr, uid, ids, context={}, *args):
        voucher_type_obj = self.pool.get('wsfe.voucher_type')

        wsfe_conf_obj = self.pool.get('wsfe.config')
        wsfe_conf = wsfe_conf_obj.get_config(cr, uid)

        wsfex_conf_obj = self.pool.get('wsfex.config')
        wsfex_conf = wsfex_conf_obj.get_config(cr, uid)

        for inv in self.browse(cr, uid, ids):
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

            conf_obj = conf._model

            # Obtenemos el tipo de comprobante
            tipo_cbte = voucher_type_obj.get_voucher_type(cr, uid, inv, context=context)

            # Obtenemos el numero de comprobante a enviar a la AFIP teniendo en
            # cuenta que inv.number == 000X-00000NN o algo similar.
            # TODO: Esto esta duplicado en los metodos de wsfe y wsfex
            inv_number = inv.internal_number
            pos, cbte_nro = inv_number.split('-')
            pos = int(pos)
            cbte_nro = int(cbte_nro)

            # Derivamos a la configuracion correspondiente
            fe_det_req = conf_obj.prepare_details(cr, uid, conf, ids, context=context)
            result = conf_obj.get_invoice_CAE(cr, uid, [conf.id], [inv.id], pos, tipo_cbte, fe_det_req, context=context)

            new_cr = False
            try:
                invoices_approbed = conf_obj._parse_result(cr, uid, [conf.id], ids, result, context=context)
                for invoice_id, invoice_vals in invoices_approbed.iteritems():
                    self.write(cr, uid, invoice_id, invoice_vals)
            except Exception, e:
                new_cr = cr.dbname
                cr.rollback()
                raise e
            finally:
                # Creamos el wsfe.request con otro cursor, porque puede pasar que
                # tengamos una excepcion e igualmente, tenemos que escribir la request
                # Sino al hacer el rollback se pierde hasta el wsfe.request
                if new_cr:
                    cr2 = pooler.get_db(new_cr).cursor()
                else:
                    cr2 = cr

                conf_obj._log_wsfe_request(cr2, uid, ids, pos, tipo_cbte, fe_det_req, result)
                if new_cr:
                    cr2.commit()
                    cr2.close()

        return True

account_invoice()
