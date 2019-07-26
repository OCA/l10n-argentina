##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class AccountPaymentOrder(models.Model):
    _name = "account.payment.order"
    _inherit = "account.payment.order"

    concept_line_ids = fields.One2many(
        comodel_name='account.payment.order.concept.line',
        inverse_name='payment_order_id', string="Other Concepts")
    other_payment = fields.Boolean('Other Payments', default=False)

    @api.depends('debt_line_ids', 'income_line_ids', 'amount',
                 'concept_line_ids')
    def _get_writeoff_amount(self):
        return super()._get_writeoff_amount()

    @api.multi
    def get_concept_lines_amount(self):
        return sum(self.concept_line_ids.mapped('amount'))

    @api.multi
    def _get_writeoff_amount_hook(self):
        amount = super()._get_writeoff_amount_hook()
        amount -= self.get_concept_lines_amount()
        return amount

    @api.multi
    def voucher_move_line_create(self, line_total, move_id,
                                 company_currency, current_currency):
        move_line_obj = self.env['account.move.line']

        res = super(AccountPaymentOrder, self).voucher_move_line_create(
            line_total, move_id, company_currency, current_currency)

        # Hacemos las lineas por cada concept_line
        tot_line, rec_lst_ids = res
        for line in self.concept_line_ids:
            if not line.amount:
                continue

            if line.payment_order_id.type == 'payment':
                amount = line.amount
            else:
                amount = line.amount * (-1)

            move_line = {
                'journal_id': self.journal_id.id,
                'name': line.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': self.partner_id.id,
                'currency_id': False,
                'analytic_account_id': line.account_analytic_id and
                line.account_analytic_id.id or False,
                'quantity': 1,
                'credit': 0.0,
                'debit': 0.0,
                'date': self.date
            }
            if amount < 0:
                amount = -amount
                tot_line -= amount
                move_line['credit'] = amount
            else:
                tot_line += amount
                move_line['debit'] = amount

            # Creamos la linea
            move_line_obj.create(move_line)

        return tot_line, rec_lst_ids


class AccountPaymentOrderConceptLine(models.Model):
    _name = "account.payment.order.concept.line"
    _desc = "Account Payment Order Concept Line"

    name = fields.Char(string='Description', size=128)
    journal_id = fields.Many2one(
        comodel_name='account.journal', string='Journal')
    account_id = fields.Many2one(
        comodel_name='account.account', string='Account', required=True)
    payment_order_id = fields.Many2one(
        comodel_name='account.payment.order', string='Voucher')
    amount = fields.Float(
        string='Amount', digits=dp.get_precision('Account'))
    account_analytic_id = fields.Many2one(
        comodel_name='account.analytic.account', string='Analytic Account')

    @api.onchange('journal_id')
    def change_journal_id(self):
        if self.journal_id:
            self.account_id = self.journal_id.default_debit_account_id.id

    @api.onchange('account_id')
    def change_account_id(self):
        journal_model = self.env['account.journal']
        if self.account_id:
            journal_ids = journal_model.search([
                ('default_debit_account_id', '=', self.account_id.id)])
            self.journal_id = journal_ids and journal_ids[0] or False
