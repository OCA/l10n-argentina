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
import re

__author__ = "Sebastian Kennedy <skennedy@e-mips.com.ar>"

class account_invoice(osv.osv):
    _name = "account.invoice"
    _inherit = "account.invoice"

#    def _get_internal_name(self, cr, uid, ids, field_name, arg, context=None):
#        res = {}
#        invoices = self.browse(cr, uid, ids, context=context)
#        for inv in invoices:
#            if inv.type in ['out_invoice', 'in_invoice']:
#                type = 'FAC'
#            elif inv.type in ['out_refund', 'in_refund']:
#                type = 'NC'
#            else:
#                type = 'ND'
#
#            pos_ar =  ''
#            if inv.pos_ar_id:
#                pos_ar = inv.pos_ar_id.name
#                if inv.denomination_id:
#                    pos_ar = inv.denomination_id.name + pos_ar
#
#            if inv.state in ('open', 'paid'):
#                res[inv.id] = type + '_' + pos_ar + '_' + inv.internal_number
#            else:
#                res[inv.id] = type + '_' + pos_ar + '_' + inv.state
#
#        return res

    _columns = {
        'aut_cae': fields.boolean('Autorizar', help='Pedido de autorizacion a la AFIP'),
        'cae': fields.char('CAE', size=32, required=False, readonly=True, help='CAE (Codigo de Autorizacion Electronico assigned by AFIP.)'),
        'cae_due_date': fields.date('CAE Due Date', required=False, readonly=True,  help='Fecha de vencimiento del CAE'),
        #'internal_name': fields.function(_get_internal_name, method=True, type='char'),
        #'associated_inv_ids': fields.many2many('account.invoice', )
    }

    _defaults = {
        'aut_cae': lambda *a: False,
    }

    # Esto lo hacemos porque al hacer una nota de credito, no le setea la fiscal_position
    # Ademas, seteamos el comprobante asociado
    def refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None):
        new_ids = super(account_invoice, self).refund(cr, uid, ids, date, period_id, description, journal_id)
        for id in new_ids:
            inv = self.browse(cr, uid, id)
            if not inv.fiscal_position:
                fiscal_position = inv.partner_id.property_account_position
                vals = {'fiscal_position':fiscal_position.id}

            # TODO: Agregamos el comprobante asociado
            # Falta terminar el codigo para hacer lo de comprobantes asociados
            self.write(cr, uid, id, vals)
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

    def _get_next_number(self, cr, uid, inv, context=None):
        wsfe_conf_obj = self.pool.get('wsfe.config')
        voucher_type_obj = self.pool.get('wsfe.voucher_type')

        conf = wsfe_conf_obj.get_config(cr, uid)

        # Obtenemos el tipo de comprobante
        tipo_cbte = voucher_type_obj.get_voucher_type(cr, uid, inv, context=context)
        try:
            pto_vta = int(inv.pos_ar_id.name)
        except ValueError:
            raise osv.except_osv('Error', 'El nombre del punto de venta tiene que ser numerico')

        res = wsfe_conf_obj.get_last_voucher(cr, uid, [conf.id], pto_vta, tipo_cbte, context=context)

        return res+1

    def action_number(self, cr, uid, ids, context=None):
        wsfe_conf_obj = self.pool.get('wsfe.config')
        conf = wsfe_conf_obj.get_config(cr, uid)
        #pos_ar_obj = self.pool.get('pos.ar')

        if not context:
            context = {}

        next_number = None
        invoice_vals = {}
        invtype = None

#        #TODO: not correct fix but required a frech values before reading it.
#        #self.write(cr, uid, ids, {})
#        context['use_internal_number'] = True

        for obj_inv in self.browse(cr, uid, ids, context=context):
            id = obj_inv.id
            invtype = obj_inv.type
            move_id = obj_inv.move_id and obj_inv.move_id.id or False
            reference = obj_inv.reference or ''

            # Chequeamos los valores fiscales
            self._check_fiscal_values(cr, uid, obj_inv)

            # si el usuario no ingreso un numero, busco el ultimo y lo incremento , si no hay ultimo va 1.
            # si el usuario hizo un ingreso dejo ese numero
            internal_number = False
            #pos_ar_name = False

            # Si son de Cliente
            if invtype in ('out_invoice', 'out_refund'):

                pos_ar = obj_inv.pos_ar_id
#                if pos_ar:
#                    pos_ar_name = pos_ar_obj.name_get(cr, uid, [pos_ar])[0][1]

                 # Chequeamos si corresponde Factura Electronica
                # Aca nos fijamos si el pos_ar_id tiene factura electronica asignada
                if obj_inv.pos_ar_id in conf.point_of_sale_ids:
                    invoice_vals['aut_cae'] = True
                    next_number = self._get_next_number(cr, uid, obj_inv, context=context)

                # Si no es Factura Electronica...
                else:
                    # Nos fijamos si el usuario dejo en blanco el campo de numero de factura
                    if not obj_inv.internal_number:
                        cr.execute("select max(to_number(internal_number, '99999999')) from account_invoice where internal_number ~ '^[0-9]+$' and pos_ar_id=%s and state in %s and type=%s", (pos_ar.id, ('open', 'paid', 'cancel',), invtype))
                        max_number = cr.fetchone()
                        # Si no devuelve resultados, es porque es el primero
                        if not max_number:
                            next_number = 1
                        else:
                            next_number = max_number[0] + 1

                # Lo ponemos como en Proveedores, o sea, A0001-00000001
                internal_number = '%s-%08d' % (pos_ar.name, next_number)
                m = re.match('^[0-9]{4}-[0-9]{8}$', internal_number)
                if not m:
                    raise osv.except_osv( _('Error'), _('The Invoice Number should be the format XXXX-XXXXXXXX'))

                # Escribimos el internal number
                invoice_vals['internal_number'] = internal_number

            # Si son de Proveedor
            else:
                m = re.match('^[0-9]{4}-[0-9]{8}$', obj_inv.internal_number)
                if not m:
                    raise osv.except_osv( _('Error'), _('The Invoice Number should be the format XXXX-XXXXXXXX'))

                internal_number = obj_inv.internal_number

            if not reference:
                # TODO: Poner el nombre de la factura toda. A0001-00000001
                # Podemos usar la funcion del l10n_ar_point_of_sale que devuelve el nombre completo
                ref = internal_number
            else:
                ref = reference

            cr.execute('UPDATE account_move SET ref=%s ' \
                    'WHERE id=%s AND (ref is null OR ref = \'\')',
                    (ref, move_id))
            cr.execute('UPDATE account_move_line SET ref=%s ' \
                    'WHERE move_id=%s AND (ref is null OR ref = \'\')',
                    (ref, move_id))
            cr.execute('UPDATE account_analytic_line SET ref=%s ' \
                    'FROM account_move_line ' \
                    'WHERE account_move_line.move_id = %s ' \
                        'AND account_analytic_line.move_id = account_move_line.id',
                        (ref, move_id))

            # Escribimos los campos necesarios de la factura
            self.write(cr, uid, obj_inv.id, invoice_vals)

            for inv_id, name in self.name_get(cr, uid, [id], context=context):
                ctx = context.copy()
                if invtype in ('out_invoice', 'out_refund'):
                    ctx = self.get_log_context(cr, uid, context=ctx)
                message = _('Invoice ') + " '" + name + "' "+ _("is validated.")
                self.log(cr, uid, inv_id, message, context=ctx)

        return True

    def hook_add_taxes(self, cr, uid, inv, detalle):
        return detalle

    def action_aut_cae(self, cr, uid, ids, context={}, *args):
        obj_precision = self.pool.get('decimal.precision')
        wsfe_conf_obj = self.pool.get('wsfe.config')
        voucher_type_obj = self.pool.get('wsfe.voucher_type')

        conf = wsfe_conf_obj.get_config(cr, uid)

        for inv in self.browse(cr, uid, ids):
            if not inv.aut_cae:
                self.write(cr, uid, ids, {'cae' : 'NA'})
                return True

            fiscal_position = inv.fiscal_position
            doc_type = inv.partner_id.document_type_id and inv.partner_id.document_type_id.afip_code or 99
            doc_num = inv.partner_id.vat

            if not fiscal_position:
                raise osv.except_osv(_('Customer Configuration Error'),
                                    _('There is no fiscal position configured for the customer %s') % inv.partner_id.name)

            # Obtenemos el tipo de comprobante
            tipo_cbte = voucher_type_obj.get_voucher_type(cr, uid, inv, context=context)

            # Obtenemos el numero de comprobante a enviar a la AFIP teniendo en
            # cuenta que inv.number == 000X-00000NN o algo similar.
            inv_number = inv.internal_number
            pos, cbte_nro = inv_number.split('-')
            pos = int(pos)
            cbte_nro = int(cbte_nro)

            detalles = []

            for inv in self.browse(cr, uid, ids):
                date_invoice = datetime.strptime(inv.date_invoice, '%Y-%m-%d')

                detalle = {}
                detalle['Concepto'] = 1 # Hardcodeado 'Productos'

                detalle['DocTipo'] = doc_type
                detalle['DocNro'] = doc_num

                #detalle['tipo_cbte'] = tipo_cbte # Factura A
                #detalle['punto_vta'] = pto_vta
                detalle['CbteDesde'] = cbte_nro
                detalle['CbteHasta'] = cbte_nro
                detalle['CbteFch'] = date_invoice.strftime('%Y%m%d')
                # TODO: Cambiar luego por la currency de la factura
                detalle['MonId'] = 'PES'
                detalle['MonCotiz'] = 1

                iva_array = []

                importe_neto = 0.0
                importe_operaciones_exentas = inv.amount_exempt
                importe_iva = 0.0
                importe_total = 0.0
                importe_neto_no_gravado = inv.amount_no_taxed


                # Procesamos las taxes
                taxes = inv.tax_line
                for tax in taxes:
                    for eitax in conf.vat_tax_ids + conf.exempt_operations_tax_ids:
                        if eitax.tax_code_id.id == tax.tax_code_id.id:
                            if eitax.exempt_operations:
                                importe_operaciones_exentas += tax.base
                            else:
                                importe_iva += tax.amount
                                importe_neto += tax.base
                                iva2 = {'Id': int(eitax.code), 'BaseImp': tax.base, 'Importe': tax.amount}
                                iva_array.append(iva2)

                importe_total = importe_neto + importe_neto_no_gravado + importe_operaciones_exentas + importe_iva
                #print 'Importe total: ', importe_total
                #print 'Importe neto gravado: ', importe_neto
                #print 'Importe IVA: ', importe_iva
                #print 'Importe Operaciones Exentas: ', importe_operaciones_exentas
                #print 'Importe neto No gravado: ', importe_neto_no_gravado
                #print 'Array de IVA: ', iva_array

                # Chequeamos que el Total calculado por el Open, se corresponda
                # con el total calculado por nosotros, tal vez puede haber un error
                # de redondeo
                prec = obj_precision.precision_get(cr, uid, 'Account')
                if round(importe_total, prec) != round(inv.amount_total, prec):
                    raise osv.except_osv(_('Error in amount_total!'), _("The total amount of the invoice does not corresponds to the total calculated." \
                        "Maybe there is an rounding error!. (Amount Calculated: %f)") % (importe_total))

                # Detalle del array de IVA
                detalle['Iva'] = iva_array

                # Detalle de los importes
                detalle['ImpOpEx'] = importe_operaciones_exentas
                detalle['ImpNeto'] = importe_neto
                detalle['ImpTotConc'] = importe_neto_no_gravado
                detalle['ImpIVA'] = importe_iva
                detalle['ImpTotal'] = inv.amount_total
                detalle['ImpTrib'] = 0.0
                detalle['Tributos'] = None

                #print 'Detalle de facturacion: ', detalle

                # Agregamos un hook para agregar tributos o IVA que pueda ser
                # llamado de otros modulos. O mismo para modificar el detalle.
                detalle = self.hook_add_taxes(cr, uid, inv, detalle)

                detalles.append(detalle)

            #print 'Detalles: ', detalles

            result = wsfe_conf_obj.get_invoice_CAE(cr, uid, [conf.id], pos, tipo_cbte, detalles, context=context)

            #print result
            # Verificamos el resultado de la Operacion

            # Si no fue aprobado
            if result['Resultado'] != 'A':
                msg = ''
                if result['Errores']:
                    msg = 'Errores: ' + result['Errores'] + '\n'
                if result['Observaciones']:
                    msg = msg + 'Observaciones: ' + result['Observaciones']

                raise osv.except_osv(_('AFIP Web Service Error'),
                                     _('La factura no fue aprobada. \n%s') % msg)
            elif result['Resultado'] == 'A' and result['Observaciones']:
                # Escribimos en el log del cliente web
                self.log(cr, uid, inv.id, result['Observaciones'], context)

            # TODO: Mejorar esto, es una chanchada
            caes = result['CAES']
            for inv in self.browse(cr, uid, ids):
                if cbte_nro in caes:
                    cae = caes[cbte_nro]['cae']
                    cae_due_date = caes[cbte_nro]['cae_vto']
                    #print 'Number: ', cbte_nro
                    #print 'CAE: ', cae
                    #print 'Vencimiento CAE: ', cae_due_date
                    self.write(cr, uid, inv.id, {'cae' : cae, 'cae_due_date' : cae_due_date})
        return True

    def action_open(self, cr, uid, ids, context={}, *args):
        self.write(cr, uid, ids, {'state':'open'}, context=context)
        return True

account_invoice()


class account_invoice_tax(osv.osv):
    _name = "account.invoice.tax"
    _inherit = "account.invoice.tax"


    def hook_compute_invoice_taxes(self, cr, uid, invoice_id, tax_grouped, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        cur = inv.currency_id

        for t in tax_grouped.values():
            # Para solucionar el problema del redondeo con AFIP
            ta = tax_obj.browse(cr, uid, t['tax_id'], context=context)
            t['amount'] = t['base']*ta.amount
            t['tax_amount'] = t['base_amount']*ta.amount

            t['base'] = cur_obj.round(cr, uid, cur, t['base'])
            t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
            t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
            t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])

        return super(account_invoice_tax, self).hook_compute_invoice_taxes(cr, uid, invoice_id, tax_grouped, context)

account_invoice_tax()
