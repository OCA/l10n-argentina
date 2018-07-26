###############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (Cardozo Nicolás Joaquin)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging
from odoo.addons import decimal_precision as dp
from odoo import models, fields, api  # , api, fields, _, exceptions
# from odoo.exceptions import except_orm
# from odoo.addons.decimal_precision import decimal_precision as dp
# from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, \
#         DEFAULT_SERVER_DATETIME_FORMAT, float_compare


_logger = logging.getLogger(__name__)


class AccountPaymentOrder(models.Model):
    _name = 'account.paymen.order'

    def _get_journal_currency(self, name, args):
        for payment in self:
            payment.currency_id = payment.journal_id.currency_id and \
                payment.journal_id.currency_id.id or \
                payment.company_id.currency_id.id

    name = fields.Char(string='Memo')
    partner_id = fields.Many2one(comodel_name='res.partner',
                                 string='Partner')
    account_id = fields.Many2one(comodel_name='account.account',
                                 string='Account')
    pay_now = fields.Selection(default='pay_now',
                               string='Payment',
                               selection=[
                                ('pay_now', 'Pay Directly'),
                                ('pay_later', 'Pay Later or Group Funds')])
    reference = fields.Char(string='Ref #')
    journal_id = fields.Many2one(comodel_name='account.journal',
                                 string='Journal')
    date = fields.Date(string='Date')
    state = fields.Selection(string='Status', selection=[
                                ('draft', 'Draft'),
                                ('cancel', 'Cancelled'),
                                ('proforma', 'Pro-forma'),
                                ('posted', 'Posted')])
    currency_id = fields.Many2one(comodel_name='res.currency',
                                  string='Currency',
                                  required=True,
                                  compute='_get_journal_currency')
    amount = fields.Float(strin='Tax Amount',
                          digits=dp.get_precision('Account'),
                          required=True)
    type = fields.selection(string='Default Type',
                            selection=[
                                ('sale', 'Sale'),
                                ('purchase', 'Purchase'),
                                ('payment', 'Payment'),
                                ('receipt', 'Receipt')])
    company_id = fields.Many2one(comodel_name='res.company',
                                 string='Company',
                                 required=True)
    pre_line = fields.Boolean(string='Previous Payments ?')
    line_cr_ids = fields.One2many(comodel_name='account.payment.order.line',
                                  string='Credits',
                                  domain=[('type', '=', 'cr')],
                                  context={'default_type': 'cr'})
    line_dr_ids = fields.One2many(comodel_name='account.payment.order.line',
                                  string='Debits',
                                  domain=[('type', '=', 'dr')],
                                  context={'default_type': 'dr'})


class AccountPaymentOrderLine(models.Model):
    _name = 'account.payment.order.line'
    _description = 'Voucher Lines'
    _order = "move_line_id"

    def _compute_balance(self):
        currency_obj = self.env['res.currency']
        

    def _currency_id(self):
        '''
        This function returns the currency id of a voucher line. It's either the currency of the
        associated move line (if any) or the currency of the voucher or the company currency.
        '''
        for line in self:
            move_line = line.move_line_id
            if move_line:
                line.currency_id = move_line.currency_id and \
                    move_line.currency_id.id or \
                    move_line.company_id.currency_id.id
            else:
                line.currency_id = line.payment_order_id.currency_id and \
                    line.payment_order_id.currency_id.id or \
                    line.payment_order_id.company_id.currency_id.id

    payment_order_id = fields.Many2one(comodel_name='account.payment.order',
                                       string='Payment Order', required=True,
                                       ondelete='cascade')
    name = fields.Char(string='Description', default='')
    account_id = fields.Many2one(comodel_name='account.account',
                                 string='Account', required=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner',
                                 related='payment_order_id.partner_id')
    untax_amount = fields.Float(string='Untax Amount')
    amount = fields.Float(string='Amount', digits=dp.get_precision('Account'))
    reconcile = fields.Boolean(string='Full Reconcile')
    type = fields.Selection(string='Dr/Cr',
                            selection=[('dr', 'Debit'),
                                       ('cr', 'Credit')])
    # account_analytic_id
    move_line_id = fields.Many2one(comodel_name='account.move.line',
                                   string='Journal Item', copy=False)
    date_original = fields.Date(string='Date',
                                related='move_line_id.date',
                                readonly=True)
    date_due = fields.Date(string='Due Date',
                           related='move_line_id.date_maturity',
                           readonly=True)
    amount_original = fields.Float(string='Original Amount',
                                   digits=dp.get_precision('Account'),
                                   compute='_compute_balance', store=True)
    amount_unreconciled = fields.Float(string='Open Balance',
                                       digits=dp.get_precision('Account'),
                                       compute='_compute_balance', store=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company',
                                 related='payment_order_id.company_id',
                                 readonly=True, store=True)
    currency_id = fields.Many2one(comodel_name='res.currency',
                                  string='Currency', readonly=True,
                                  compute='_currency_id')
    state = fields.Char(string='State', readonly=True,
                        related='payment_order_id.state')

    @api.onchange('amount')
    def onchange_amount(self):
        if self.amount:
            self.reconcile = (round(self.amount, 2) == round(self.amount_unreconciled, 2))
