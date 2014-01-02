# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2011
# 
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
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from osv import osv, fields
import decimal_precision as dp
import time

class retention_tax_line(osv.osv):
    _name = "retention.tax.line"
    _description = "Retention Tax Line"

    #TODO: Tal vaz haya que ponerle estados a este objeto para manejar tambien propiedades segun estados
    _columns = {
        'name': fields.char('Retention', required=True, size=64),
        'date': fields.date('Date', select=True),
        'voucher_id': fields.many2one('account.voucher', 'Voucher', ondelete='cascade'),
        'voucher_number': fields.related('voucher_id', 'number', type='char', string='Voucher No.'),
        'account_id': fields.many2one('account.account', 'Tax Account', required=True,
                                      domain=[('type','<>','view'),('type','<>','income'), ('type', '<>', 'closed')]),
        'base': fields.float('Base', digits_compute=dp.get_precision('Account')),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account')),
        'retention_id': fields.many2one('retention.retention', 'Retention Configuration', required=True, help="Retention configuration used '\
                                       'for this retention tax, where all the configuration resides. Accounts, Tax Codes, etc."),
        'base_code_id': fields.many2one('account.tax.code', 'Base Code', help="The account basis of the tax declaration."),
        'base_amount': fields.float('Base Code Amount', digits_compute=dp.get_precision('Account')),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Code', help="The tax basis of the tax declaration."),
        'tax_amount': fields.float('Tax Code Amount', digits_compute=dp.get_precision('Account')),
        'company_id': fields.related('account_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'partner_id': fields.related('voucher_id', 'partner_id', type='many2one', relation='res.partner', string='Partner', readonly=True),
        'vat': fields.related('voucher_id', 'partner_id', 'vat', type='char', string='CIF/NIF', readonly=True),
        'certificate_no': fields.char('Certificate No.', required=False, size=32),
        'state_id': fields.many2one('res.country.state', string="State/Province"),
    }

    _defaults = {
        #'date': lambda *a: time.strftime('%Y-%m-%d'),
    }

    def onchange_retention(self, cr, uid, ids, retention_id, context):
        if not retention_id:
            return {}

        retention_obj = self.pool.get('retention.retention')
        retention = retention_obj.browse(cr, uid, retention_id)
        vals = {}
        vals['name'] = retention.name
        vals['account_id'] = retention.tax_id.account_collected_id.id
        vals['base_code_id'] = retention.tax_id.base_code_id.id
        vals['tax_code_id'] = retention.tax_id.tax_code_id.id

        if retention.state_id:
            vals['state_id'] = retention.state_id.id
        else:
            vals['state_id'] = False

        return {'value': vals}

    def create_voucher_move_line(self, cr, uid, retention, voucher, context=None):
        voucher_obj = self.pool.get('account.voucher')

        move_lines = []

        if retention.amount == 0.0:
            return move_lines

        # Chequeamos si esta seteada la fecha, sino le ponemos la fecha del voucher
        retention_vals = {}
        if not retention.date:
            retention_vals['date'] = voucher.date

        company_currency = voucher.company_id.currency_id.id
        current_currency = voucher.currency_id.id

        tax_amount_in_company_currency =  voucher_obj._convert_paid_amount_in_company_currency(cr, uid, voucher, retention.amount, context=context)
        base_amount_in_company_currency =  voucher_obj._convert_paid_amount_in_company_currency(cr, uid, voucher, retention.base, context=context)

        debit = credit = 0.0

       # Lo escribimos en el objeto retention_tax_line
        retention_vals['tax_amount'] = tax_amount_in_company_currency
        retention_vals['base_amount'] = base_amount_in_company_currency

        #retention_obj.write(cr, uid, retention.id, retention_vals)

        debit = credit = 0.0
        if voucher.type in ('purchase', 'payment'):
            credit = tax_amount_in_company_currency
        elif voucher.type in ('sale', 'receipt'):
            debit = tax_amount_in_company_currency
        if debit < 0: credit = -debit; debit = 0.0
        if credit < 0: debit = -credit; credit = 0.0
        sign = debit - credit < 0 and -1 or 1

        # Creamos la linea contable perteneciente a la retencion
        move_line = {
            'name': retention.name or '/',
            'debit': debit,
            'credit': credit,
            'account_id': retention.account_id.id,
            'tax_code_id': retention.tax_code_id.id,
            'tax_amount': tax_amount_in_company_currency,
            #'move_id': move_id,
            'journal_id': voucher.journal_id.id,
            'period_id': voucher.period_id.id,
            'partner_id': voucher.partner_id.id,
            'currency_id': company_currency <> current_currency and  current_currency or False,
            'amount_currency': company_currency <> current_currency and sign * retention.amount or 0.0,
            'date': voucher.date,
            'date_maturity': voucher.date_due
        }

        move_lines.append(move_line)

        # ...y ahora creamos la linea contable perteneciente a la base imponible de la retencion
        # Notar que credit & debit son 0.0 ambas. Lo que cuenta es el tax_code_id y el tax_amount
        move_line = {
            'name': retention.name + '(Base Imp)',
            'ref': voucher.name,
            'debit': 0.0,
            'credit': 0.0,
            'account_id': retention.account_id.id,
            'tax_code_id': retention.base_code_id.id,
            'tax_amount': base_amount_in_company_currency,
            #'move_id': move_id,
            'journal_id': voucher.journal_id.id,
            'period_id': voucher.period_id.id,
            'partner_id': voucher.partner_id.id,
            'currency_id': False, #company_currency <> current_currency and  current_currency or False,
            'amount_currency': 0.0, #company_currency <> current_currency and sign * retention.amount or 0.0,
            'date': voucher.date,
            'date_maturity': voucher.date_due
        }

        move_lines.append(move_line)
        return move_lines



retention_tax_line()


class account_voucher(osv.osv):
    _name = 'account.voucher'
    _inherit = 'account.voucher'

    _columns = {
            'retention_ids': fields.one2many('retention.tax.line', 'voucher_id', 'Retentions', readonly=True, states={'draft':[('readonly', False)]}),
            }

    def _get_retention_amount(self, cr, uid, retention_ids, context=None):
        retention_line_obj = self.pool.get('retention.tax.line')
        amount = 0.0

        for retention_line in retention_ids:
            if retention_line[0] == 4 and retention_line[1] and not retention_line[2]:
                am = retention_line_obj.read(cr, uid, retention_line[1], ['amount'], context=context)['amount']
                if am:
                    amount += float(am)
            if retention_line[2]:
                amount += retention_line[2]['amount']

        return amount


    def onchange_payment_line(self, cr, uid, ids, amount, payment_line_ids, issued_check_ids, third_check_ids, third_check_receipt_ids, retention_ids, context=None):

        amount = self._get_payment_lines_amount(cr, uid, payment_line_ids, context)
        amount += self._get_issued_checks_amount(cr, uid, issued_check_ids, context)
        amount += self._get_third_checks_amount(cr, uid, third_check_ids, context)
        amount += self._get_third_checks_receipt_amount(cr, uid, third_check_receipt_ids, context)
        amount += self._get_retention_amount(cr, uid, retention_ids, context)

        return {'value': {'amount': amount}}

    def onchange_third_receipt_checks(self, cr, uid, ids, amount, payment_line_ids, third_check_receipt_ids, retention_ids, context=None):

        amount = self._get_payment_lines_amount(cr, uid, payment_line_ids, context)
        amount += self._get_third_checks_receipt_amount(cr, uid, third_check_receipt_ids, context)
        amount += self._get_retention_amount(cr, uid, retention_ids, context)

        return {'value': {'amount': amount}}

    def onchange_issued_checks(self, cr, uid, ids, amount, payment_line_ids, issued_check_ids, third_check_ids, retention_ids, context=None):

        amount = self._get_payment_lines_amount(cr, uid, payment_line_ids, context)
        amount += self._get_issued_checks_amount(cr, uid, issued_check_ids, context)
        amount += self._get_third_checks_amount(cr, uid, third_check_ids, context)
        amount += self._get_retention_amount(cr, uid, retention_ids, context)

        return {'value': {'amount': amount}}

    def onchange_third_checks(self, cr, uid, ids, amount, payment_line_ids, issued_check_ids, third_check_ids, retention_ids, context=None):

        amount = self._get_payment_lines_amount(cr, uid, payment_line_ids, context)
        amount += self._get_issued_checks_amount(cr, uid, issued_check_ids, context)
        amount += self._get_third_checks_amount(cr, uid, third_check_ids, context)
        amount += self._get_retention_amount(cr, uid, retention_ids, context)

        return {'value': {'amount': amount}}

    def onchange_retentions(self, cr, uid, ids, amount, payment_line_ids, issued_check_ids, third_check_ids, third_check_receipt_ids, retention_ids, context=None):

        amount = self._get_payment_lines_amount(cr, uid, payment_line_ids, context)
        amount += self._get_issued_checks_amount(cr, uid, issued_check_ids, context)
        amount += self._get_third_checks_amount(cr, uid, third_check_ids, context)
        amount += self._get_third_checks_receipt_amount(cr, uid, third_check_receipt_ids, context)
        amount += self._get_retention_amount(cr, uid, retention_ids, context)

        return {'value': {'amount': amount}}

    def create_move_line_hook(self, cr, uid, voucher_id, move_id, move_lines, context={}):
        retention_line_obj = self.pool.get("retention.tax.line")
        move_lines = super(account_voucher, self).create_move_line_hook(cr, uid, voucher_id, move_id, move_lines, context=context)
        voucher = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)

        for ret in voucher.retention_ids:

            res = retention_line_obj.create_voucher_move_line(cr, uid, ret, voucher, context=context)
            if res:
                res[0]['move_id'] = move_id
                res[1]['move_id'] = move_id
                move_lines.append(res[0])
                move_lines.append(res[1])

        return move_lines

#    def create_move_line_hook(self, cr, uid, voucher_id, move_id, move_lines, context={}):
#        move_lines = super(account_voucher, self).create_move_line_hook(cr, uid, voucher_id, move_id, move_lines, context=context)
#
#        currency_pool = self.pool.get('res.currency')
#        retention_obj = self.pool.get('retention.tax.line')
#
#        v = self.browse(cr, uid, voucher_id)
#
#        context_multi_currency = context.copy()
#        context_multi_currency.update({'date': v.date})
#
#        for r in v.retention_ids:
#            if r.amount == 0.0:
#                continue
#
#            # Chequeamos si esta seteada la fecha, sino le ponemos la fecha del voucher
#            retention_vals = {}
#            if not r.date:
#                retention_vals['date'] = v.date
#
#            # TODO: Chequear que funcione bien en multicurrency estas dos lineas de abajo
#            company_currency = v.journal_id.company_id.currency_id.id
#            current_currency = v.currency_id.id
#
#            debit = 0.0
#            credit = 0.0
#            # TODO: is there any other alternative then the voucher type ??
#            # -for sale, purchase we have but for the payment and receipt we do not have as based on the bank/cash journal we can not know its payment or receipt
#            # Calculamos el tax_amount y el base_amount basados en las currency de la compania y del voucher
#            # TODO: Esto tendriamos que hacerlo en el mismo objeto retention_tax_line
#            tax_amount = currency_pool.compute(cr, uid, v.currency_id.id, company_currency, r.amount, context=context_multi_currency, round=False)
#            base_amount = currency_pool.compute(cr, uid, v.currency_id.id, company_currency, r.base, context=context_multi_currency, round=False)
#
#
#           # Lo escribimos en el objeto retention_tax_line
#            retention_vals['tax_amount'] = tax_amount
#            retention_vals['base_amount'] = base_amount
#
#            retention_obj.write(cr, uid, r.id, retention_vals)
#
#            if v.type in ('purchase', 'payment'):
#                credit = tax_amount
#            elif v.type in ('sale', 'receipt'):
#                debit = tax_amount
#            if debit < 0:
#                credit = -debit
#                debit = 0.0
#            if credit < 0:
#                debit = -credit
#                credit = 0.0
#            sign = debit - credit < 0 and -1 or 1
#
#            # Creamos la linea contable perteneciente a la retencion
#            move_line = {
#                'name': r.name or '/',
#                'debit': debit,
#                'credit': credit,
#                'account_id': r.account_id.id,
#                'tax_code_id': r.tax_code_id.id,
#                'tax_amount': tax_amount,
#                'move_id': move_id,
#                'journal_id': v.journal_id.id,
#                'period_id': v.period_id.id,
#                'partner_id': v.partner_id.id,
#                'currency_id': company_currency <> current_currency and  current_currency or False,
#                'amount_currency': company_currency <> current_currency and sign * r.amount or 0.0,
#                'date': v.date,
#                'date_maturity': v.date_due
#            }
#
#            move_lines.append(move_line)
#
#            # ...y ahora creamos la linea contable perteneciente a la base imponible de la retencion
#            # Notar que credit & debit son 0.0 ambas. Lo que cuenta es el tax_code_id y el tax_amount
#            move_line = {
#                'name': r.name + '(Base Imp)',
#                'ref': v.name,
#                'debit': 0.0,
#                'credit': 0.0,
#                'account_id': r.account_id.id,
#                'tax_code_id': r.base_code_id.id,
#                'tax_amount': base_amount,
#                'move_id': move_id,
#                'journal_id': v.journal_id.id,
#                'period_id': v.period_id.id,
#                'partner_id': v.partner_id.id,
#                'currency_id': company_currency <> current_currency and  current_currency or False,
#                'amount_currency': company_currency <> current_currency and sign * r.amount or 0.0,
#                'date': v.date,
#                'date_maturity': v.date_due
#            }
#
#            move_lines.append(move_line)
#        return move_lines

account_voucher()
