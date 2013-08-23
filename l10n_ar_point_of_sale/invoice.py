# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2008-2011 E-MIPS Electronica e Informatica <info@e-mips.com.ar>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from osv import osv, fields
from tools.translate import _
import decimal_precision as dp
import time
import re

class invoice(osv.osv):
    _name = "account.invoice"
    _inherit = "account.invoice"
    _order = "internal_number desc"

    def name_get(self, cr, uid, ids, context=None):

        if not ids:
            return []

        if not context:
            context = {}

        res = []
        types = {
                'out_invoice': _('CI '),
                'in_invoice': _('SI '),
                'out_refund': _('CR '),
                'in_refund': _('SR '),
                'out_debit': _('CD '),
                'in_debit': _('SD '),
                }

        if not context.get('use_internal_number', True):
            res = super(invoice, self).name_get( cr, uid, ids, context=context)
        else:
            reads = self.read(cr, uid, ids, ['pos_ar_id', 'type', 'is_debit_note', 'internal_number', 'denomination_id'], context=context)
            for record in reads:
                type = record['type']
                rtype = type
                number = record['internal_number'] or ''
                denom = record['denomination_id'] and record['denomination_id'][1] or ''
                debit_note = record['is_debit_note']

                # Chequeo de Nota de Debito
                if type == 'out_invoice':
                    if debit_note:
                        rtype = 'out_debit'
                    else:
                        rtype = 'out_invoice'
                elif type == 'in_invoice':
                    if debit_note:
                        rtype = 'in_debit'
                    else:
                        rtype = 'in_invoice'

                name = types[rtype] + denom + number
                res.append((record['id'], name))

        return res

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []

        if not context.get('use_internal_number', True):
            return super(invoice, self).name_search( cr, user, name, args, operator, context=context, limit=limit)
        else:
            if name:
                ids = self.search(cr, user, [('internal_number','=',name)] + args, limit=limit, context=context)
            if not ids:
                ids = self.search(cr, user, [('internal_number',operator,name)] + args, limit=limit, context=context)
            if not ids:
                try:
                    ids = self.search(cr, user, [('pos_ar.name',operator,name)] + args, limit=limit, context=context)
                except TypeError:
                    ids = []

        return self.name_get(cr, user, ids, context)

    def _amount_all_ar(self, cr, uid, ids, name, args, context=None):
        res = {}

        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'amount_taxed': 0.0,
                'amount_no_taxed': 0.0,
                'amount_exempt': 0.0
            }

            amount_base = 0.0
            amount_exempt = 0.0

            for line in invoice.invoice_line:
                res[invoice.id]['amount_untaxed'] += line.price_subtotal
            for line in invoice.tax_line:
                if line.tax_id.tax_group == 'vat':
                    if line.is_exempt:
                        amount_exempt += line.base
                    else:
                        amount_base += line.base

                res[invoice.id]['amount_tax'] += line.amount

            res[invoice.id]['amount_total'] = res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed']
            res[invoice.id]['amount_no_taxed'] = res[invoice.id]['amount_untaxed'] - amount_base - amount_exempt
            res[invoice.id]['amount_taxed'] = amount_base
            res[invoice.id]['amount_exempt'] = amount_exempt
        return res

    def _get_invoice_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.invoice.line').browse(cr, uid, ids, context=context):
            result[line.invoice_id.id] = True
        return result.keys()

    def _get_invoice_tax(self, cr, uid, ids, context=None):
        result = {}
        for tax in self.pool.get('account.invoice.tax').browse(cr, uid, ids, context=context):
            result[tax.invoice_id.id] = True
        return result.keys()

    _columns = {
        'type': fields.selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Supplier Invoice'),
            ('out_refund','Customer Refund'),
            ('in_refund','Supplier Refund'),
            ],'Type', readonly=True, select=True, change_default=True),
        'pos_ar_id' : fields.many2one('pos.ar','Point of Sale'),
        'is_debit_note': fields.boolean('Debit Note'),
        'denomination_id' : fields.many2one('invoice.denomination','Denomination'),
        'internal_number': fields.char('Invoice Number', size=32, help="Unique number of the invoice, computed automatically when the invoice is created."),
        'amount_exempt': fields.function(_amount_all_ar, method=True, digits_compute=dp.get_precision('Account'), string='Amount Exempt',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
            },
            multi='all'),
        'amount_no_taxed': fields.function(_amount_all_ar, method=True, digits_compute=dp.get_precision('Account'), string='No Taxed',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
            },
            multi='all'),
        'amount_taxed': fields.function(_amount_all_ar, method=True, digits_compute=dp.get_precision('Account'), string='Taxed',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
            },
            multi='all'),
        'amount_untaxed': fields.function(_amount_all_ar, method=True, digits_compute=dp.get_precision('Account'), string='Untaxed',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
            },
            multi='all'),
        'amount_tax': fields.function(_amount_all_ar, method=True, digits_compute=dp.get_precision('Account'), string='Tax',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
            },
            multi='all'),
        'amount_total': fields.function(_amount_all_ar, method=True, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
            },
            multi='all'),
    }

    _defaults = {
            'is_debit_note': lambda *a: False,
            }

    def _check_fiscal_values(self, cr, uid, inv):
        # Si es factura de cliente
        denomination_id = inv.denomination_id and inv.denomination_id.id
        if inv.type in ('out_invoice', 'out_refund', 'out_debit'):

            if not denomination_id:
                raise osv.except_osv(_('Error!'), _('Denomination not set in invoice'))
#                if inv.pos_ar_id.denomination_id:
#                    self.write(cr, uid, inv.id, {'denomination_id' : inv.pos_ar_id.denomination_id.id})
#                    denomination_id = inv.pos_ar_id.denomination_id.id
#                else:
#                    raise osv.except_osv(_('Error!'), _('Denomination not set neither in invoice nor point of sale'))
#            else:
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

    def action_number(self, cr, uid, ids, context=None):
        pos_ar_obj = self.pool.get('pos.ar')
        if context is None:
            context = {}
        #TODO: not correct fix but required a frech values before reading it.
        self.write(cr, uid, ids, {})

        for obj_inv in self.browse(cr, uid, ids, context=context):
            id = obj_inv.id
            invtype = obj_inv.type
            move_id = obj_inv.move_id and obj_inv.move_id.id or False
            reference = obj_inv.reference or ''

#del        self.write(cr, uid, ids, {'internal_number':number})
#add:
        #~ si el usuario no ingreso un numero, busco el ultimo y lo incremento , si no hay ultimo va 1.
        #~ si el usuario hizo un ingreso dejo ese numero
            internal_number = False
            pos_ar = obj_inv.pos_ar_id.id
            pos_ar_name = False
            if pos_ar:
                pos_ar_name = pos_ar_obj.name_get(cr, uid, [pos_ar])[0][1]

            self._check_fiscal_values(cr, uid, obj_inv)

            if not obj_inv.internal_number:
                max_number = []
                if obj_inv.type in ('out_invoice', 'out_refund', 'out_debit'):
                    cr.execute("select max(to_number(internal_number, '99999999')) from account_invoice where internal_number ~ '^[0-9]+$' and pos_ar_id=%s and state in %s and type='out_invoice'", (pos_ar, ('open', 'paid', 'cancel',)))
                    max_number = cr.fetchone()
                if not max_number:
                    internal_number = '%08d' % 1
                    self.write(cr, uid, id, {'internal_number' : internal_number })
                else:
                    if not max_number[0]:
                        max_number = 0
                    else:
                        max_number = max_number[0]
                    internal_number = '%08d' % ( int(max_number) + 1)
                    self.write(cr, uid, id, {'internal_number' : internal_number })
            else :
                # Si es factura de proveedor
                if obj_inv.type in ['in_invoice', 'in_refund', 'in_debit']:
                    m = re.match('^[0-9]{4}-[0-9]{8}$', obj_inv.internal_number)
                    if not m:
                        raise osv.except_osv( _('Error'),
                                            _('The Invoice Number should be the format XXXX-XXXXXXXX'))
                    internal_number = obj_inv.internal_number
#                    # Chequeamos que la posicion fiscal y la denomination_id coincidan
#                    if obj_inv.fiscal_position.denom_supplier_id.id != obj_inv.denomination_id.id:
#                        raise osv.except_osv( _('Error'),
#                                            _('The invoice denomination does not corresponds with this fiscal position.'))
#
#                    # Chequeamos que la posicion fiscal de la factura y del cliente tambien coincidan
#                    if obj_inv.fiscal_position.id != obj_inv.partner_id.property_account_position.id:
#                        raise osv.except_osv( _('Error'),
#                                            _('The invoice fiscal position is not the same as the partner\'s fiscal position.'))

                # Si es de cliente
                else:
                    try:
                        int(obj_inv.internal_number)
                    except :
                        raise osv.except_osv( _('Error'),
                                            _('The Invoice Number can not contain characters'))
                    internal_number = ('%08d' % int(obj_inv.internal_number))

#                    # Chequeamos que la posicion fiscal y la denomination_id coincidan
#                    if obj_inv.fiscal_position.denomination_id.id != obj_inv.denomination_id.id:
#                        raise osv.except_osv( _('Error'),
#                                            _('The invoice denomination does not corresponds with this fiscal position.'))
#
#                    # Chequeamos que la posicion fiscal de la factura y del cliente tambien coincidan
#                    if obj_inv.fiscal_position.id != obj_inv.partner_id.property_account_position.id:
#                        raise osv.except_osv( _('Error'),
#                                            _('The invoice fiscal position is not the same as the partner\'s fiscal position.'))

                self.write(cr, uid, id, {'internal_number' : internal_number})
#end add
            if invtype in ('in_invoice', 'in_refund', 'in_debit'):
                if not reference:
#mod                #self._convert_ref(cr, uid, internal_number)   
                    ref = internal_number 
                else:
                    ref = reference
            else:
#mod            #ref = self._convert_ref(cr, uid, number)
                ref = pos_ar_name + ' ' + internal_number

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

            for inv_id, name in self.name_get(cr, uid, [id]):
                ctx = context.copy()
                if obj_inv.type in ('out_invoice', 'out_refund'):
                    ctx = self.get_log_context(cr, uid, context=ctx)
                message = _('Invoice ') + " '" + name + "' "+ _("is validated.")
                self.log(cr, uid, inv_id, message, context=ctx)
        return True


    def refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None):

        #devuelve los ids de las invoice modificadas
        inv_ids = super(invoice , self).refund(cr, uid, ids, date, period_id, description, journal_id)

        #busco los puntos de venta de las invoices anteriores
        inv_obj = self.browse(cr, uid , ids , context=None)
        for obj in inv_obj:
            self.write(cr, uid , inv_ids , {'pos_ar_id': obj.pos_ar_id.id, 'denomination_id': obj.denomination_id.id} , context=None)

        return inv_ids

    def onchange_partner_id(self, cr, uid, ids, type, partner_id,\
            date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False , context=None):
        res =   super(invoice, self).onchange_partner_id(cr, uid, ids, type, partner_id,\
                date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False)

        if partner_id:

            fiscal_position_id = res['value']['fiscal_position']

            # HACK: Si no encontramos una fiscal position, buscamos una property que nos de el default
            # En realidad, si tenemos esa property creada desde el principio, todos los partners tendrian
            # su posicion fiscal. Pero si ya tenemos varios partners creados sin posicion fiscal, leemos
            # la property que creamos de la posicion fiscal para que quede como default y asi no tenemos
            # que hacerle muchas modificaciones al sistema. Igualmente, al setear una property que sea Global
            # ya no hace falta buscarla por codigo porque se la asigna solito a todos los que no tenian.
            if not fiscal_position_id:
                property_obj = self.pool.get('ir.property')
                fpos_pro_id = property_obj.search(cr, uid, [('name','=','property_account_position'),('company_id','=',company_id)])
                if not fpos_pro_id:
                    return res
                fpos_line_data = property_obj.read(cr, uid, fpos_pro_id, ['name','value_reference','res_id'])

                fiscal_position_id = fpos_line_data and fpos_line_data[0].get('value_reference',False) and int(fpos_line_data[0]['value_reference'].split(',')[1]) or False

            fiscal_pool = self.pool.get('account.fiscal.position')
            pos_pool = self.pool.get('pos.ar')
            if fiscal_position_id:
                fiscal_position = fiscal_pool.browse(cr, uid , fiscal_position_id)
                denomination_id = fiscal_position.denomination_id.id
                res.update({'domain': {'pos_ar_id': [('denomination_id', '=', denomination_id)]}})

                #para las invoices de suppliers
                if type in ['in_invoice', 'in_refund', 'in_debit']:
                    denom_sup_id = fiscal_pool.browse(cr, uid , fiscal_position_id).denom_supplier_id.id
                    res['value'].update({'denomination_id': denom_sup_id})
                #para las customers invoices
                else:
                    pos = pos_pool.search( cr, uid , [('denomination_id','=',denomination_id)] , limit=1 )
                    if len(pos):
                        res['value'].update({'pos_ar_id': pos[0]})
                        res['value'].update({'denomination_id': denomination_id})
        return res

    def invoice_pay_customer(self, cr, uid, ids, context=None):
        if not ids: return []
        inv = self.browse(cr, uid, ids[0], context=context)
        res = super(invoice, self).invoice_pay_customer(cr, uid, ids, context=context)
        res['context']['type'] = inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'

        return res

invoice()


class account_invoice_tax(osv.osv):
    _name = "account.invoice.tax"
    _inherit = "account.invoice.tax"

    _columns = {
        'tax_id': fields.many2one('account.tax', 'Account Tax', readonly=True),
        'is_exempt': fields.boolean('Is Exempt', readonly=True),
            }

    def hook_compute_invoice_taxes(self, cr, uid, invoice_id, tax_grouped, context=None):
        return tax_grouped

    def compute(self, cr, uid, invoice_id, context=None):

        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        cur = inv.currency_id
        company_currency = inv.company_id.currency_id.id

        for line in inv.invoice_line:
            for tax in tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, (line.price_unit* (1-(line.discount or 0.0)/100.0)), line.quantity, inv.address_invoice_id.id, line.product_id, inv.partner_id)['taxes']:
                val={}
                # TODO: Tal vez se pueda cambiar el boolean is_exempt por un type (selection)
                # para despues incluir impuestos internos, retenciones, percepciones, o sea,
                # distintos tipos de impuestos
                is_exempt = tax_obj.read(cr, uid, tax['id'], ['is_exempt'], context)['is_exempt']
                val['invoice_id'] = inv.id
                val['name'] = tax['name']
                val['amount'] = tax['amount']
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['is_exempt'] = is_exempt
                val['base'] = tax['price_unit'] * line['quantity']
                val['tax_id'] = tax['id']

                if inv.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = cur_obj.round(cr, uid, cur, t['base'])
            t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
            t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
            t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])

        # Agregamos un hook por si otros modulos quieren agregar sus taxes
        tax_grouped = self.hook_compute_invoice_taxes(cr, uid, invoice_id, tax_grouped, context)

        return tax_grouped

account_invoice_tax()
