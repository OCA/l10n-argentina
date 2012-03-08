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

class retention_tax_line(osv.osv):
    _name = "retention.tax.line"
    _description = "Retention Tax Line"

    #TODO: Tal vaz haya que ponerle estados a este objeto para manejar tambien propiedades segun estados
    _columns = {
        'name': fields.char('Retention', required=True, size=64),
        'voucher_id': fields.many2one('account.voucher', 'Voucher'),
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
        #'factor_base': fields.function(_count_factor, method=True, string='Multipication factor for Base code', type='float', multi="all"),
        #'factor_tax': fields.function(_count_factor, method=True, string='Multipication factor Tax code', type='float', multi="all")
        'certificate_no': fields.char('Certificate No.', required=True, size=32),
    }

    def onchange_retention(self, cr, uid, ids, retention_id, context):
        print 'onchange_retention: ', retention_id
        retention_obj = self.pool.get('retention.retention')
        retention = retention_obj.browse(cr, uid, retention_id)
        vals = {}
        vals['name'] = retention.name
        vals['account_id'] = retention.tax_id.account_collected_id.id
        vals['base_code_id'] = retention.tax_id.base_code_id.id
        vals['tax_code_id'] = retention.tax_id.tax_code_id.id
        return {'value': vals}

    #TODO: Calculo del base_amount y todo eso. Ver invoice.py:1582
    #def compute(self, cr, uid, ids, etc, etc):
    #   pass

retention_tax_line()


class account_voucher(osv.osv):
    _name = 'account.voucher'
    _inherit = 'account.voucher'

    def _total_amount(self, cr, uid, ids, name, arg, context=None):
        vouchers = super(account_voucher, self)._total_amount(cr, uid, ids, name, arg, context=context)

        for v in vouchers:
            voucher = self.browse(cr, uid, v)
            amount = 0.0
            # Sumamos los importes de las retenciones
            for r in voucher.retention_ids:
                amount += r.amount

            vouchers[v] += amount
        return vouchers

    _columns = {
            'retention_ids': fields.one2many('retention.tax.line', 'voucher_id', 'Retentions', readonly=True, states={'draft':[('readonly', False)]}),
              'amount': fields.function(_total_amount, method=True, type='float',  string='Paid Amount'),
            }

    def onchange_retentions(self, cr, uid, ids, retention_ids, context):
        #res={'value':{'amount':1.0}}
        res={'value':{}}
        return res

    def create_move_line_hook(self, cr, uid, voucher_id, move_id, move_lines, context={}):
        move_lines = super(account_voucher, self).create_move_line_hook(cr, uid, voucher_id, move_id, move_lines, context=context)

        currency_pool = self.pool.get('res.currency')
        retention_obj = self.pool.get('retention.tax.line')

        v = self.browse(cr, uid, voucher_id)

        context_multi_currency = context.copy()
        context_multi_currency.update({'date': v.date})

        for r in v.retention_ids:
            if r.amount == 0.0:
                continue

            # TODO: Chequear que funcione bien en multicurrency estas dos lineas de abajo
            company_currency = v.journal_id.company_id.currency_id.id
            current_currency = v.currency_id.id

            debit = 0.0
            credit = 0.0
            # TODO: is there any other alternative then the voucher type ??
            # -for sale, purchase we have but for the payment and receipt we do not have as based on the bank/cash journal we can not know its payment or receipt
            # Calculamos el tax_amount y el base_amount basados en las currency de la compania y del voucher
            # TODO: Esto tendriamos que hacerlo en el mismo objeto retention_tax_line
            tax_amount = currency_pool.compute(cr, uid, v.currency_id.id, company_currency, r.amount, context=context_multi_currency, round=False)
            base_amount = currency_pool.compute(cr, uid, v.currency_id.id, company_currency, r.base, context=context_multi_currency, round=False)

            # Lo escribimos en el objeto retention_tax_line
            retention_obj.write(cr, uid, r.id, {'tax_amount': tax_amount, 'base_amount': base_amount})

            if v.type in ('purchase', 'payment'):
                credit = tax_amount
            elif v.type in ('sale', 'receipt'):
                debit = tax_amount
            if debit < 0:
                credit = -debit
                debit = 0.0
            if credit < 0:
                debit = -credit
                credit = 0.0
            sign = debit - credit < 0 and -1 or 1

            # Creamos la linea contable perteneciente a la retencion
            move_line = {
                'name': r.name or '/',
                'debit': debit,
                'credit': credit,
                'account_id': r.account_id.id,
                'tax_code_id': r.tax_code_id.id,
                'tax_amount': tax_amount,
                'move_id': move_id,
                'journal_id': v.journal_id.id,
                'period_id': v.period_id.id,
                'partner_id': v.partner_id.id,
                'currency_id': company_currency <> current_currency and  current_currency or False,
                'amount_currency': company_currency <> current_currency and sign * r.amount or 0.0,
                'date': v.date,
                'date_maturity': v.date_due
            }

            move_lines.append(move_line)

            # ...y ahora creamos la linea contable perteneciente a la base imponible de la retencion
            # Notar que credit & debit son 0.0 ambas. Lo que cuenta es el tax_code_id y el tax_amount
            move_line = {
                'name': r.name or '/',
                'ref': v.name,
                'debit': 0.0,
                'credit': 0.0,
                'account_id': r.account_id.id,
                'tax_code_id': r.base_code_id.id,
                'tax_amount': base_amount,
                'move_id': move_id,
                'journal_id': v.journal_id.id,
                'period_id': v.period_id.id,
                'partner_id': v.partner_id.id,
                'currency_id': company_currency <> current_currency and  current_currency or False,
                'amount_currency': company_currency <> current_currency and sign * r.amount or 0.0,
                'date': v.date,
                'date_maturity': v.date_due
            }

            move_lines.append(move_line)
            return move_lines

account_voucher()
