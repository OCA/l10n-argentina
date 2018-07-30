###############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (Cardozo Nicolás Joaquin)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging
from odoo.addons import decimal_precision as dp
from odoo import models, fields, api, _  # , api, fields, _, exceptions
from odoo.exceptions import RedirectWarning, ValidationError
# from odoo.addons.decimal_precision import decimal_precision as dp
# from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, \
#         DEFAULT_SERVER_DATETIME_FORMAT, float_compare


_logger = logging.getLogger(__name__)


class AccountPaymentOrder(models.Model):
    _name = 'account.payment.order'

    def _get_journal_currency(self, name, args):
        for payment in self:
            payment.currency_id = payment.journal_id.currency_id and \
                payment.journal_id.currency_id.id or \
                payment.company_id.currency_id.id

    def _get_journal(self):
        ttype = self.env.context.get('type', 'bank')

        # Pago inmediato, al contado, desde el boton de la factura
        immediate = self.env.context.get('immediate_payment', False)

        if not immediate and ttype in ('payment', 'receipt'):
            rec = self.env['account.journal'].search(
                [('type', '=', ttype)], limit=1,
                order='priority')
            if not rec:
                action = self.env.ref('account.action_account_journal_form')
                msg = ('Cannot find a Payment/Receipt journal. \
                  \nPlease create at least one.')
                raise RedirectWarning(
                  msg, action.id, _('Go to the journal configuration'))

    def _get_writeoff_amount(self):
        if not self:
            self.writeoff_amount = ''
        for payment in self:
            debit = credit = 0.0
            sign = payment.type == 'payment' and -1 or 1
            for l in payment.line_dr_ids:
                debit += l.amount
            for l in payment.line_cr_ids:
                credit += l.amount
            currency = payment.currency_id or payment.company_id.currency_id
            amount = payment.amount - sign * (credit - debit)
        self.writeoff_amount = currency.round(amount)

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
                                 string='Journal', required=True,
                                 default=_get_journal)
    move_id = fields.Many2one(comodel_name='account.move',
                              string='Account Entry',
                              copy=False)
    move_line_ids = fields.One2many(comodel_name='account.move.line',
                                    related='move_id.line_ids',
                                    string='Journal Items',
                                    readonly=True)
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
    writeoff_amount = fields.Float(string='Difference Amount',
                                   compute='_get_writeoff_amount',
                                   readonly=True,
                                   help="Computed as the difference between \
                                   the amount stated in the voucher and the \
                                   sum of allocation on the voucher lines.")
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
    payment_mode_line_id = fields.One2many(
        comodel_name='account.payment.mode.line',
        inverse_name='payment_order_id',
        string='Payments Lines')
    line_cr_ids = fields.One2many(comodel_name='account.payment.order.line',
                                  inverse_name='payment_order_id',
                                  string='Credits',
                                  domain=[('type', '=', 'cr')],
                                  context={'default_type': 'cr'})
    line_dr_ids = fields.One2many(comodel_name='account.payment.order.line',
                                  inverse_name='payment_order_id',
                                  string='Debits',
                                  domain=[('type', '=', 'dr')],
                                  context={'default_type': 'dr'})

    def _get_payment_lines_amount(self):
        amount = 0.0
        for payment_line in self.payment_mode_line_id:
            amount += float(payment_line.amount)
        return amount

    @api.onchange('payment_mode_line_id')
    def onchange_payment_line(self):
        amount = self._get_payment_lines_amount()
        self.amount = amount

    # TODO: onchange_partner_id()  -  _get_payment_lines_default()

    @api.multi
    def _clean_payment_lines(self):
        for payment_line in self.payment_mode_line_id:
            if payment_line.amount == 0:
                payment_line.unlink()
        return True

    @api.multi
    def proforma_voucher(self):
        # Chequeamos si la writeoff_amount no es negativa
        if round(self.writeoff_amount, 2) < 0.0:
            raise ValidationError(_('Error ! Cannot validate a \
              voucher with negative amount. Please check \
              that Writeoff Amount is not negative.'))

        self._clean_payment_lines()
        self.action_move_line_create()

        return True

    def _get_company_currency(self):
        '''
        Get the currency of the actual company.

        :param voucher_id: Id of the voucher what i want to obtain company currency.
        :return: currency id of the company of the voucher
        :rtype: int
        '''
        return self.journal_id.company_id.currency_id.id

    def _get_current_currency(self):
        '''
        Get the currency of the voucher.

        :param voucher_id: Id of the voucher what i want to obtain current currency.
        :return: currency id of the voucher
        :rtype: int
        '''
        return self.currency_id.id or self._get_company_currency()

    @api.multi
    def action_move_line_create(self):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        move_pool = self.env['account.move']
        move_line_pool = self.env['account.move.line']
        for payment in self:
            if payment.move_id:
                continue
            company_currency = payment._get_company_currency()
            current_currency = payment._get_current_currency()


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
            round_amount = round(self.amount, 2)
            round_unreconciled = round(self.amount_unreconciled, 2)
            self.reconcile = (round_amount == round_unreconciled)

class AccountPaymentModeLine(models.Model):
    _name = 'account.payment.mode.line'
    _description = 'Payment method lines'

    @api.depends('payment_mode_id')
    def _compute_currency(self):
        for i in self:
            i.currency_id = i.payment_mode_id.currency_id.id

    @api.model
    def _get_company_currency(self):
        currency_obj = self.env['res.currency']
        if self.env.user.company_id:
            return self.env.user.company_id.currency_id.id
        else:
            return currency_obj.search([('rate', '=', 1.0)], limit=1).id

    name = fields.Char(help='Payment reference',
                       string='Mode',
                       required=True,
                       readonly=True,
                       size=64)
    payment_mode_id = fields.Many2one(comodel_name='account.journal',
                                      string='Payment Method')
    amount = fields.Float(string='Amount',
                          digits=(16, 2),
                          default=0.0,
                          required=False,
                          help='Payment amount in the company currency')
    amount_currency = fields.Float(
        string='Amount in Partner Currency',
        digits=(16, 2), required=False,
        help='Payment amount in the partner currency')
    currency_id = fields.Many2one(comodel_name='res.currency',
                                  compute='_compute_currency',
                                  string='Currency',
                                  store=True)
    company_currency = fields.Many2one(comodel_name='res.currency',
                                       string='Company Currency',
                                       default=_get_company_currency,
                                       readonly=False)
    date = fields.Date(string='Payment Date',
                       help="This date is informative only.")
