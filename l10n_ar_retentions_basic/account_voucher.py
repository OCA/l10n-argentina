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

from openerp import models, fields, api
from openerp.addons import decimal_precision as dp


class retention_tax_line(models.Model):
    _name = "retention.tax.line"
    _description = "Retention Tax Line"

    # TODO: Tal vaz haya que ponerle estados a este objeto para manejar tambien propiedades segun estados
    name = fields.Char('Retention', size=64)
    date = fields.Date('Date', select=True)
    voucher_id = fields.Many2one('account.voucher', 'Voucher', ondelete='cascade')
    voucher_number = fields.Char('Reference', size=64)
    account_id = fields.Many2one('account.account', 'Tax Account', required=True, domain=[('type', '<>', 'view'), ('type', '<>', 'income'), ('type', '<>', 'closed')])
    base = fields.Float('Base', digits=dp.get_precision('Account'))
    amount = fields.Float('Amount', digits=dp.get_precision('Account'))
    retention_id = fields.Many2one('retention.retention', 'Retention Configuration', required=True, help="Retention configuration used for this retention tax, where all the configuration resides. Accounts, Tax Codes, etc.")
    base_code_id = fields.Many2one('account.tax.code', 'Base Code', help="The account basis of the tax declaration.")
    base_amount = fields.Float('Base Code Amount', digits=dp.get_precision('Account'))
    tax_code_id = fields.Many2one('account.tax.code', 'Tax Code', help="The tax basis of the tax declaration.")
    tax_amount = fields.Float('Tax Code Amount', digits=dp.get_precision('Account'))
    company_id = fields.Many2one(string='Company', related='account_id.company_id', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', 'Partner', required=False)
    vat = fields.Char(string='CIF/NIF', related='partner_id.vat', readonly=True)
    certificate_no = fields.Char('Certificate No.', required=False, size=32)
    state_id = fields.Many2one('res.country.state', string="State/Province")

    @api.onchange('retention_id')
    def onchange_retention(self):
        retention = self.retention_id
        if retention.id:
            self.name = retention.name
            self.account_id = retention.tax_id.account_collected_id.id
            self.base_code_id = retention.tax_id.base_code_id.id
            self.tax_code_id = retention.tax_id.tax_code_id.id

            if retention.state_id:
                self.state_id = retention.state_id.id
            else:
                self.state_id = False

    @api.model
    def create_voucher_move_line(self):
        """
        Params
        self = retention.tax.line
        """
        self.ensure_one()
        voucher = self.voucher_id
        retention = self
        move_lines = []

        if retention.amount == 0.0:
            return move_lines

        # Chequeamos si esta seteada la fecha, sino le ponemos la fecha del voucher
        retention_vals = {}
        if not retention.date:
            retention_vals['date'] = voucher.date

        company_currency = voucher.company_id.currency_id.id
        current_currency = voucher.currency_id.id

        tax_amount_in_company_currency = voucher._convert_paid_amount_in_company_currency(retention.amount)
        base_amount_in_company_currency = voucher._convert_paid_amount_in_company_currency(retention.base)

        debit = credit = 0.0

        # Lo escribimos en el objeto retention_tax_line
        # retention_vals['tax_amount'] = tax_amount_in_company_currency
        # retention_vals['base_amount'] = base_amount_in_company_currency

        retention.write(retention_vals)

        debit = credit = 0.0
        if voucher.type in ('purchase', 'payment'):
            credit = tax_amount_in_company_currency
        elif voucher.type in ('sale', 'receipt'):
            debit = tax_amount_in_company_currency
        if debit < 0:
            credit = -debit
            debit = 0.0
        if credit < 0:
            debit = -credit
            credit = 0.0
        sign = debit - credit < 0 and -1 or 1

        # Creamos la linea contable perteneciente a la retencion
        move_line = {
            'name': retention.name or '/',
            'debit': debit,
            'credit': credit,
            'account_id': retention.account_id.id,
            'tax_code_id': retention.tax_code_id.id,
            'tax_amount': tax_amount_in_company_currency,
            # 'move_id': move_id,
            'journal_id': voucher.journal_id.id,
            'period_id': voucher.period_id.id,
            'partner_id': voucher.partner_id.id,
            'currency_id': company_currency != current_currency and current_currency or False,
            'amount_currency': company_currency != current_currency and sign * retention.amount or 0.0,
            'date': voucher.date,
            'date_maturity': voucher.date_due
        }

        move_lines.append(move_line)

        # ...y ahora creamos la linea contable perteneciente a la base imponible de la retencion
        # Notar que credit & debit son 0.0 ambas. Lo que cuenta es el tax_code_id y el tax_amount
        move_line = {
            'name': retention.name + '(Base Imp)',
            # 'ref': voucher.name,
            'debit': 0.0,
            'credit': 0.0,
            'account_id': retention.account_id.id,
            'tax_code_id': retention.base_code_id.id,
            'tax_amount': base_amount_in_company_currency,
            # 'move_id': move_id,
            'journal_id': voucher.journal_id.id,
            'period_id': voucher.period_id.id,
            'partner_id': voucher.partner_id.id,
            'currency_id': False,  # company_currency <> current_currency and  current_currency or False,
            'amount_currency': 0.0,  # company_currency <> current_currency and sign * retention.amount or 0.0,
            'date': voucher.date,
            'date_maturity': voucher.date_due
        }

        move_lines.append(move_line)
        return move_lines


retention_tax_line()


class account_voucher(models.Model):
    _name = 'account.voucher'
    _inherit = 'account.voucher'

    retention_ids = fields.One2many('retention.tax.line', 'voucher_id', 'Retentions', readonly=True, states={'draft': [('readonly', False)]})

    @api.multi
    def _get_retention_amount(self):
        amount = 0.0
        for retention_line in self.retention_ids:
            am = retention_line.amount
            if am:
                amount += float(am)
        return amount

    @api.onchange('payment_line_ids')
    def onchange_payment_line(self):
        amount = self._get_payment_lines_amount()
        amount += self._get_issued_checks_amount()
        amount += self._get_third_checks_amount()
        amount += self._get_third_checks_receipt_amount()
        amount += self._get_retention_amount()

        self.amount = amount

    @api.onchange('third_check_receipt_ids')
    def onchange_third_receipt_checks(self):
        amount = self._get_payment_lines_amount()
        amount += self._get_third_checks_receipt_amount()
        amount += self._get_retention_amount()
        self.amount = amount

    @api.onchange('issued_check_ids')
    def onchange_issued_checks(self):
        amount = self._get_payment_lines_amount()
        amount += self._get_issued_checks_amount()
        amount += self._get_third_checks_amount()
        amount += self._get_retention_amount()
        self.amount = amount

    @api.onchange('third_check_ids')
    def onchange_third_checks(self):
        amount = self._get_payment_lines_amount()
        amount += self._get_issued_checks_amount()
        amount += self._get_third_checks_amount()
        amount += self._get_retention_amount()
        self.amount = amount

    @api.onchange('retention_ids')
    def onchange_retentions(self):
        amount = self._get_payment_lines_amount()
        amount += self._get_issued_checks_amount()
        amount += self._get_third_checks_amount()
        amount += self._get_third_checks_receipt_amount()
        amount += self._get_retention_amount()
        self.amount = amount

    @api.multi
    def create_move_line_hook(self, move_id, move_lines):
        voucher = self
        move_lines = super(account_voucher, self).create_move_line_hook(move_id, move_lines)

        for ret in voucher.retention_ids:
            res = ret.create_voucher_move_line()
            if res:
                res[0]['move_id'] = move_id
                res[1]['move_id'] = move_id
                move_lines.append(res[0])
                move_lines.append(res[1])

            # Escribimos valores del voucher en la retention tax line
            ret_vals = {
                'voucher_number': voucher.reference,
                'partner_id': voucher.partner_id.id,
            }
            ret.write(ret_vals)

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
