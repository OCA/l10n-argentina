# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012-2014 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#    All Rights Reserved. See AUTHORS for details.
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
from tools.translate import _
import decimal_precision as dp
import time
import re

class invoice(osv.osv):
    _name = "account.invoice"
    _inherit = "account.invoice"
    _order = "date_invoice desc, internal_number desc"

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
                    ids = self.search(cr, user, [('pos_ar_id.name',operator,name)] + args, limit=limit, context=context)
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
        'pos_ar_id' : fields.many2one('pos.ar','Point of Sale', readonly=True, states={'draft':[('readonly',False)]}),
        'is_debit_note': fields.boolean('Debit Note'),
        'denomination_id' : fields.many2one('invoice.denomination','Denomination', readonly=True, states={'draft':[('readonly',False)]}),
        'internal_number': fields.char('Invoice Number', size=32, readonly=True, states={'draft':[('readonly',False)]}, help="Unique number of the invoice, computed automatically when the invoice is created."),
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

    def _check_duplicate(self, cr, uid, ids, context=None):
        partner_obj = self.pool.get('res.partner')
        company_obj = self.pool.get('res.company')
        for invoice in self.read(cr, uid, ids, ['denomination_id', 'pos_ar_id', 'type', 'is_debit_note', 'internal_number', 'partner_id', 'state', 'company_id'], context=context):

            denomination_id = invoice['denomination_id'] and invoice['denomination_id'][0] or False
            pos_ar_id = invoice['pos_ar_id'] and invoice['pos_ar_id'][0] or False
            partner_id = invoice['partner_id'] and invoice['partner_id'][0] or False
            company_id = invoice['company_id'] and invoice['company_id'][0] or False

            partner_country = partner_obj.read(cr, uid, partner_id, ['country_id'], context=context)['country_id']
            company_country = company_obj.read(cr, uid, company_id, ['country_id'], context=context)['country_id']

            if invoice['type'] in ('in_invoice', 'in_refund'):
                local = ((partner_country and partner_country[0]) == (company_country and company_country[0])) or partner_country == False

                # Si no es local, no hacemos chequeos
                if not local:
                    return True

            # Si la factura no tiene seteado el numero de factura, devolvemos True, porque no sabemos si estara
            # duplicada hasta que no le pongan el numero
            if not invoice['internal_number']:
                return True

            if invoice['type'] in ['out_invoice', 'out_refund']:
                count = self.search_count(cr, uid, [('denomination_id','=',denomination_id), ('pos_ar_id','=',pos_ar_id), ('is_debit_note','=',invoice['is_debit_note']), ('internal_number','!=', False), ('internal_number','!=',''), ('internal_number','=',invoice['internal_number']), ('type','=',invoice['type']), ('state','!=','cancel')])
                if count > 1:
                    return False
            else:
                count = self.search_count(cr, uid, [('denomination_id','=',denomination_id), ('is_debit_note','=',invoice['is_debit_note']), ('partner_id','=',partner_id), ('internal_number','!=', False), ('internal_number','!=',''), ('internal_number','=', invoice['internal_number']), ('type','=',invoice['type']), ('state','!=','cancel')])
                if count > 1:
                    return False
        return True

    _constraints = [
        (_check_duplicate, 'Error! The Invoice is duplicated.', ['denomination_id', 'pos_ar_id', 'type', 'is_debit_note', 'internal_number'])
    ]

    def _check_fiscal_values(self, cr, uid, inv):
        # Si es factura de cliente
        denomination_id = inv.denomination_id and inv.denomination_id.id
        if inv.type in ('out_invoice', 'out_refund', 'out_debit'):

            if not denomination_id:
                raise osv.except_osv(_('Error!'), _('Denomination not set in invoice'))

            if not inv.fiscal_position:
                raise osv.except_osv(_('Error!'), _('Fiscal Position not set in invoice'))
#                if inv.pos_ar_id.denomination_id:
#                    self.write(cr, uid, inv.id, {'denomination_id' : inv.pos_ar_id.denomination_id.id})
#                    denomination_id = inv.pos_ar_id.denomination_id.id
#                else:
#                    raise osv.except_osv(_('Error!'), _('Denomination not set neither in invoice nor point of sale'))
#            else:
            if not inv.pos_ar_id:
                raise osv.except_osv(_('Error!'), _('You have to select a Point of Sale.'))

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


    def _update_reference(self, cr, uid, obj_inv, ref, context=None):

        move_id = obj_inv.move_id and obj_inv.move_id.id or False
        cr.execute('UPDATE account_move SET ref=%s ' \
                'WHERE id=%s', # AND (ref is null OR ref = \'\')',
                (ref, move_id))
        cr.execute('UPDATE account_move_line SET ref=%s ' \
                'WHERE move_id=%s', # AND (ref is null OR ref = \'\')',
                (ref, move_id))
        cr.execute('UPDATE account_analytic_line SET ref=%s ' \
                'FROM account_move_line ' \
                'WHERE account_move_line.move_id = %s ' \
                    'AND account_analytic_line.move_id = account_move_line.id',
                    (ref, move_id))
        return True

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

    def action_number(self, cr, uid, ids, context=None):

        if context is None:
            context = {}

        next_number = None
        invoice_vals = {}
        invtype = None

        #TODO: not correct fix but required a fresh values before reading it
        # Esto se usa para forzar a que recalcule los campos funcion
        self.write(cr, uid, ids, {})

        for obj_inv in self.browse(cr, uid, ids, context=context):
            partner_country = obj_inv.partner_id.country_id and obj_inv.partner_id.country_id.id or False
            company_country = obj_inv.company_id.country_id and obj_inv.company_id.country_id.id or False

            id = obj_inv.id
            invtype = obj_inv.type

            if invtype in ('in_invoice', 'in_refund'):
                local = (partner_country == company_country) or partner_country == False
            else:
                local = True

            #move_id = obj_inv.move_id and obj_inv.move_id.id or False
            reference = obj_inv.reference or ''

            if local:
                self._check_fiscal_values(cr, uid, obj_inv)

            # si el usuario no ingreso un numero, busco el ultimo y lo incremento , si no hay ultimo va 1.
            # si el usuario hizo un ingreso dejo ese numero
            internal_number = False
            next_number = False

            # Si son de Cliente
            if invtype in ('out_invoice', 'out_refund'):

                pos_ar = obj_inv.pos_ar_id
                next_number = self.get_next_invoice_number(cr, uid, obj_inv, context=context)

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


            for inv_id, name in self.name_get(cr, uid, [id], context=context):
                ctx = context.copy()
                if invtype in ('out_invoice', 'out_refund'):
                    ctx = self.get_log_context(cr, uid, context=ctx)
                message = _('Invoice ') + " '" + name + "' "+ _("is validated.")
                self.log(cr, uid, inv_id, message, context=ctx)

        return True

    def _refund_cleanup_lines(self, cr, uid, lines):
        for line in lines:
            if line.get('tax_id'):
                line['tax_id'] = line['tax_id'][0]
        return super(invoice, self)._refund_cleanup_lines(cr, uid, lines)

    def refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None, context=None):

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
                    pos = pos_pool.search( cr, uid , [('denomination_id','=',denomination_id)], order='priority asc', limit=1 )
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
        'tax_id': fields.many2one('account.tax', 'Account Tax', required=True),
        'is_exempt': fields.boolean('Is Exempt', readonly=True),
            }

    def tax_id_change(self, cr, uid, ids, tax_id, invoice_type):
        tax_obj = self.pool.get('account.tax')

        tax = tax_obj.browse(cr, uid, tax_id)

        val = {}
        val['name'] = tax.description
        if invoice_type in ('out_invoice','in_invoice'):
            val['base_code_id'] = tax.base_code_id.id
            val['tax_code_id'] = tax.tax_code_id.id
            val['account_id'] = tax.account_collected_id.id
        else:
            val['base_code_id'] = tax.ref_base_code_id.id
            val['tax_code_id'] = tax.ref_tax_code_id.id
            val['account_id'] = tax.account_paid_id.id

        return {'value': val}


    def hook_compute_invoice_taxes(self, cr, uid, invoice_id, tax_grouped, context=None):
        return tax_grouped

    def compute(self, cr, uid, invoice_id, context=None):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        cur = inv.currency_id
        company_currency = inv.company_id.currency_id.id

        ctx = context.copy()
        if not 'date' in ctx:
            ctx['date'] = inv.date_invoice or time.strftime('%Y-%m-%d')

        for line in inv.invoice_line:
            for tax in tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, (line.price_unit* (1-(line.discount or 0.0)/100.0)), line.quantity, line.product_id, inv.partner_id)['taxes']:
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
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['base_sign'], context=ctx, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context=ctx, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context=ctx, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context=ctx, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_paid_id']

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'], val['account_analytic_id'])
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
        tax_grouped = self.hook_compute_invoice_taxes(cr, uid, invoice_id, tax_grouped, ctx)

        return tax_grouped

account_invoice_tax()
