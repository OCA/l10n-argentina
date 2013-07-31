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
import time
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


    # Heredamos esta funcion para quitarle el post de los asientos contables
    # asi luego los podemos cancelar en caso que sea necesario
    def action_move_create(self, cr, uid, ids, *args):
        """Creates invoice related analytics and financial move lines"""

        ait_obj = self.pool.get('account.invoice.tax')
        cur_obj = self.pool.get('res.currency')
        context = {}
        for inv in self.browse(cr, uid, ids):
            if not inv.journal_id.sequence_id:
                raise osv.except_osv(_('Error !'), _('Please define sequence on invoice journal'))
            if not inv.invoice_line:
                raise osv.except_osv(_('No Invoice Lines !'), _('Please create some invoice lines.'))
            if inv.move_id:
                continue

            if not inv.date_invoice:
                self.write(cr, uid, [inv.id], {'date_invoice':time.strftime('%Y-%m-%d')})
            company_currency = inv.company_id.currency_id.id
            # create the analytical lines
            # one move line per invoice line
            iml = self._get_analytic_lines(cr, uid, inv.id)
            # check if taxes are all computed
            ctx = context.copy()
            ctx.update({'lang': inv.partner_id.lang})
            compute_taxes = ait_obj.compute(cr, uid, inv.id, context=ctx)
            self.check_tax_lines(cr, uid, inv, compute_taxes, ait_obj)

            if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding/2.0):
                raise osv.except_osv(_('Bad total !'), _('Please verify the price of the invoice !\nThe real total does not match the computed total.'))

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'procent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise osv.except_osv(_('Error !'), _("Cannot create the invoice !\nThe payment term defined gives a computed amount greater than the total invoiced amount."))

            # one move line per tax line
            iml += ait_obj.move_line_get(cr, uid, inv.id)

            entry_type = ''
            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
                entry_type = 'journal_pur_voucher'
                if inv.type == 'in_refund':
                    entry_type = 'cont_voucher'
            else:
                ref = self._convert_ref(cr, uid, inv.number)
                entry_type = 'journal_sale_vou'
                if inv.type == 'out_refund':
                    entry_type = 'cont_voucher'

            diff_currency_p = inv.currency_id.id <> company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total = 0
            total_currency = 0
            total, total_currency, iml = self.compute_invoice_totals(cr, uid, inv, company_currency, ref, iml)
            acc_id = inv.account_id.id

            name = inv['name'] or '/'
            totlines = False
            if inv.payment_term:
                totlines = self.pool.get('account.payment.term').compute(cr,
                        uid, inv.payment_term.id, total, inv.date_invoice or False)
            if totlines:
                res_amount_currency = total_currency
                i = 0
                for t in totlines:
                    if inv.currency_id.id != company_currency:
                        amount_currency = cur_obj.compute(cr, uid,
                                company_currency, inv.currency_id.id, t[1])
                    else:
                        amount_currency = False

                    # last line add the diff
                    res_amount_currency -= amount_currency or 0
                    i += 1
                    if i == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': acc_id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency_p \
                                and  amount_currency or False,
                        'currency_id': diff_currency_p \
                                and inv.currency_id.id or False,
                        'ref': ref,
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': acc_id,
                    'date_maturity': inv.date_due or False,
                    'amount_currency': diff_currency_p \
                            and total_currency or False,
                    'currency_id': diff_currency_p \
                            and inv.currency_id.id or False,
                    'ref': ref
            })

            date = inv.date_invoice or time.strftime('%Y-%m-%d')
            part = inv.partner_id.id

            line = map(lambda x:(0,0,self.line_get_convert(cr, uid, x, part, date, context={})),iml)

            line = self.group_lines(cr, uid, iml, line, inv)

            journal_id = inv.journal_id.id
            journal = self.pool.get('account.journal').browse(cr, uid, journal_id)
            if journal.centralisation:
                raise osv.except_osv(_('UserError'),
                        _('Cannot create invoice move on centralised journal'))

            line = self.finalize_invoice_move_lines(cr, uid, inv, line)

            move = {
                'ref': inv.reference and inv.reference or inv.name,
                'line_id': line,
                'journal_id': journal_id,
                'date': date,
                'type': entry_type,
                'narration':inv.comment
            }
            period_id = inv.period_id and inv.period_id.id or False
            if not period_id:
                period_ids = self.pool.get('account.period').search(cr, uid, [('date_start','<=',inv.date_invoice or time.strftime('%Y-%m-%d')),('date_stop','>=',inv.date_invoice or time.strftime('%Y-%m-%d')), ('company_id', '=', inv.company_id.id)])
                if period_ids:
                    period_id = period_ids[0]
            if period_id:
                move['period_id'] = period_id
                for i in line:
                    i[2]['period_id'] = period_id

            move_id = self.pool.get('account.move').create(cr, uid, move, context=context)
            new_move_name = self.pool.get('account.move').browse(cr, uid, move_id).name
            # make the invoice point to that move
            self.write(cr, uid, [inv.id], {'move_id': move_id,'period_id':period_id, 'move_name':new_move_name})

#            # Pass invoice in context in method post: used if you want to get the same
#            # account move reference when creating the same invoice after a cancelled one:
#            self.pool.get('account.move').post(cr, uid, [move_id], context={'invoice':inv})
        self._log_event(cr, uid, ids)
        return True



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

    def _update_reference(self, cr, uid, obj_inv, ref, context=None):

        move_id = obj_inv.move_id and obj_inv.move_id.id or False
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
        return True

    def action_number(self, cr, uid, ids, context=None):
        wsfe_conf_obj = self.pool.get('wsfe.config')
        conf = wsfe_conf_obj.get_config(cr, uid)

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
            reference = obj_inv.reference or ''

            # Chequeamos los valores fiscales
            self._check_fiscal_values(cr, uid, obj_inv)

            # si el usuario no ingreso un numero, busco el ultimo y lo incremento , si no hay ultimo va 1.
            # si el usuario hizo un ingreso dejo ese numero
            internal_number = False

            # Si son de Cliente
            if invtype in ('out_invoice', 'out_refund'):

                pos_ar = obj_inv.pos_ar_id

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
                        if not max_number or not max_number[0]:
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

            # Actulizamos el campo reference del move_id correspondiente a la creacion de la factura
            self._update_reference(cr, uid, obj_inv, ref, context=context)

            # Como sacamos el post de action_move_create, lo tenemos que poner aqui
            # Lo sacamos para permitir la validacion por lote. Ver wizard account.invoice.confirm
            move_id = obj_inv.move_id and obj_inv.move_id.id or False
            self.pool.get('account.move').post(cr, uid, [move_id], context={'invoice':obj_inv})

            # Escribimos los campos necesarios de la factura
            self.write(cr, uid, obj_inv.id, invoice_vals)

            for inv_id, name in self.name_get(cr, uid, [id], context=context):
                ctx = context.copy()
                if invtype in ('out_invoice', 'out_refund'):
                    ctx = self.get_log_context(cr, uid, context=ctx)
                message = _('Invoice ') + " '" + name + "' "+ _("is validated.")
                self.log(cr, uid, inv_id, message, context=ctx)

        return True

    def wsfe_invoice_prepare_detail(self, cr, uid, ids, context=None):
        wsfe_conf_obj = self.pool.get('wsfe.config')
        conf = wsfe_conf_obj.get_config(cr, uid)
        obj_precision = self.pool.get('decimal.precision')

        details = []

        first_num = context.get('first_num', False)
        cbte_nro = 0

        for inv in self.browse(cr, uid, ids):
            detalle = {}

            fiscal_position = inv.fiscal_position
            doc_type = inv.partner_id.document_type_id and inv.partner_id.document_type_id.afip_code or 99
            doc_num = inv.partner_id.vat

            if not fiscal_position:
                raise osv.except_osv(_('Customer Configuration Error'),
                                    _('There is no fiscal position configured for the customer %s') % inv.partner_id.name)

            # Obtenemos el numero de comprobante a enviar a la AFIP teniendo en
            # cuenta que inv.number == 000X-00000NN o algo similar.
            if not inv.internal_number:
                if not first_num:
                    raise osv.except_osv(_("WSFE Error!"), _("There is no first invoice number declared!"))
                inv_number = first_num
            else:
                inv_number = inv.internal_number

            if not cbte_nro:
                cbte_nro = inv_number.split('-')[1]
                cbte_nro = int(cbte_nro)
            else:
                cbte_nro = cbte_nro + 1

            date_invoice = datetime.strptime(inv.date_invoice, '%Y-%m-%d')

            detalle['invoice_id'] = inv.id

            detalle['Concepto'] = 1 # Hardcodeado 'Productos'
            detalle['DocTipo'] = doc_type
            detalle['DocNro'] = doc_num
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
#            print 'Importe total: ', importe_total
#            print 'Importe neto gravado: ', importe_neto
#            print 'Importe IVA: ', importe_iva
#            print 'Importe Operaciones Exentas: ', importe_operaciones_exentas
#            print 'Importe neto No gravado: ', importe_neto_no_gravado
#            print 'Array de IVA: ', iva_array

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

            details.append(detalle)

        #print 'Detalles: ', details
        return details

    def hook_add_taxes(self, cr, uid, inv, detalle):
        return detalle

    def action_aut_cae(self, cr, uid, ids, context={}, *args):
        wsfe_conf_obj = self.pool.get('wsfe.config')
        voucher_type_obj = self.pool.get('wsfe.voucher_type')

        conf = wsfe_conf_obj.get_config(cr, uid)

        for inv in self.browse(cr, uid, ids):
            if not inv.aut_cae:
                self.write(cr, uid, ids, {'cae' : 'NA'})
                return True

            # Obtenemos el tipo de comprobante
            tipo_cbte = voucher_type_obj.get_voucher_type(cr, uid, inv, context=context)

            # Obtenemos el numero de comprobante a enviar a la AFIP teniendo en
            # cuenta que inv.number == 000X-00000NN o algo similar.
            inv_number = inv.internal_number
            pos, cbte_nro = inv_number.split('-')
            pos = int(pos)
            cbte_nro = int(cbte_nro)

            fe_det_req = self.wsfe_invoice_prepare_detail(cr, uid, ids, context=context)

            result = wsfe_conf_obj.get_invoice_CAE(cr, uid, [conf.id], [inv.id], pos, tipo_cbte, fe_det_req, context=context)
            self._parse_result(cr, uid, ids, result, context=context)

        return True

    def _parse_result(self, cr, uid, ids, result, context=None):

        if not context:
            context = {}

        invoices_approbed = []

        # Verificamos el resultado de la Operacion
        # Si no fue aprobado
        if result['Resultado'] == 'R':
            msg = ''
            if result['Errores']:
                msg = 'Errores: ' + result['Errores'] + '\n'

            if context.get('raise-exception', True):
                raise osv.except_osv(_('AFIP Web Service Error'),
                                     _('La factura no fue aprobada. \n%s') % msg)

        elif result['Resultado'] == 'A' or result['Resultado'] == 'P':
            index = 0
            for inv in self.browse(cr, uid, ids):
                invoice_vals = {}
                comp = result['Comprobantes'][index]
                if comp['Observaciones']:
                    msg = 'Observaciones: ' + '\n'.join(comp['Observaciones'])

                    ## Escribimos en el log del cliente web
                    #self.log(cr, uid, inv.id, msg, context)

                # Chequeamos que se corresponda con la factura que enviamos a validar
                doc_type = inv.partner_id.document_type_id and inv.partner_id.document_type_id.afip_code or 99
                doc_tipo = comp['DocTipo'] == int(doc_type)
                doc_num = comp['DocNro'] == int(inv.partner_id.vat)
                cbte = True
                if inv.internal_number:
                    cbte = comp['CbteHasta'] == int(inv.internal_number.split('-')[1])
                else:
                    # TODO: El nro de factura deberia unificarse para que se setee en una funcion
                    # o algo asi para que no haya posibilidad de que sea diferente nunca en su formato
                    invoice_vals['internal_number'] = '%04d-%08d' % (result['PtoVta'], comp['CbteHasta'])

                if not all([doc_tipo, doc_num, cbte]):
                    raise osv.except_osv(_("WSFE Error!"), _("Validated invoice that not corresponds!"))

                if comp['Resultado'] == 'A':
                    invoice_vals['cae'] = comp['CAE']
                    invoice_vals['cae_due_date'] = comp['CAEFchVto']
                    self.write(cr, uid, inv.id, invoice_vals)
                    invoices_approbed.append(inv.id)

                index += 1

        return invoices_approbed

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
