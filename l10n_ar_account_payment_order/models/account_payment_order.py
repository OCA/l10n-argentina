##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from datetime import datetime

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import RedirectWarning, ValidationError, UserError
from odoo.tools import float_compare


class AccountPaymentOrder(models.Model):
    _name = 'account.payment.order'
    _inherit = ['mail.thread']
    _rec_name = 'number'
    _order = 'date DESC'

    name = fields.Char(
        string='Memo', default='')
    number = fields.Char(
        string='Number', copy=False, states={
            'cancel': [('readonly', True)],
            'posted': [('readonly', True)],
        })
    narration = fields.Text(
        string='Notes', default=lambda s: s._get_narration())
    partner_id = fields.Many2one(
        comodel_name='res.partner', string='Partner', states={
            'cancel': [('readonly', True)],
            'posted': [('readonly', True)],
        }, default=lambda s: s._get_partner())
    account_id = fields.Many2one(
        comodel_name='account.account', string='Account')
    pay_now = fields.Selection(
        default='pay_now', string='Payment', selection=[
            ('pay_now', 'Pay Directly'),
            ('pay_later', 'Pay Later or Group Funds')])
    reference = fields.Char(
        string='Ref #', default=lambda s: s._get_reference())
    journal_id = fields.Many2one(
        comodel_name='account.journal', string='Journal',
        required=True, states={
            'cancel': [('readonly', True)],
            'posted': [('readonly', True)],
        }, default=lambda s: s._get_journal())
    move_id = fields.Many2one(
        comodel_name='account.move', string='Account Entry', copy=False)
    move_line_ids = fields.One2many(comodel_name='account.move.line',
                                    related='move_id.line_ids',
                                    string='Journal Items')
    date = fields.Date(string='Date',
                       states={
                           'cancel': [('readonly', True)],
                           'posted': [('readonly', True)]
                       },
                       default=lambda self: self._context.get(
                           'date', fields.Date.context_today(self)))
    date_due = fields.Date(string="Due Date")
    state = fields.Selection(
        string='Status', selection=[
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('proforma', 'Pro-forma'),
            ('posted', 'Posted')],
        default='draft', readonly=True)
    currency_id = fields.Many2one(
        comodel_name='res.currency', string='Currency',
        compute='_get_journal_currency')
    amount = fields.Float(
        string='Tax Amount', digits=dp.get_precision('Account'),
        default=lambda s: s._get_amount(), states={
            'cancel': [('readonly', True)],
            'posted': [('readonly', True)],
        }, required=True)
    writeoff_acc_id = fields.Many2one(
        comodel_name='account.account', states={
            'cancel': [('readonly', True)],
            'posted': [('readonly', True)],
        }, string='Counterpart Account')
    comment = fields.Char(
        string='Counterpart Comment', default=_('Write-Off'), required=True)
    analytic_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Write-Off Analytic Account')
    writeoff_amount = fields.Float(
        string='Difference Amount', compute='_get_writeoff_amount',
        readonly=True,
        help="Computed as the difference between the amount stated " +
        "in the voucher and the sum of allocation on the voucher lines.")
    type = fields.Selection(
        string='Default Type', selection=[
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
            ('payment', 'Payment'),
            ('receipt', 'Receipt')], default=lambda s: s._get_type())
    tax_id = fields.Many2one(
        comodel_name='account.tax', string='Tax', readonly=True,
        domain=[('price_include', '=', False)],
        help="Only for tax excluded from price")
    payment_option = fields.Selection(
        string='Payment Difference',
        required=True,
        selection=[
            ('without_writeoff', 'Keep Open'),
            ('with_writeoff', 'Reconcile Payment Balance')],
        default='without_writeoff',
        help="This field helps you to choose what you want \
        to do with the eventual difference between the paid \
        amount and the sum of allocated amounts. You can either \
        choose to keep open this difference on the partner's \
        account, or reconcile it with the payment(s)")
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company',
        default=lambda s: s._get_default_company(),
        required=True, readonly=True)
    pre_line = fields.Boolean(string='Previous Payments ?')
    payment_mode_line_ids = fields.One2many(
        comodel_name='account.payment.mode.line',
        inverse_name='payment_order_id',
        states={
            'cancel': [('readonly', True)],
            'posted': [('readonly', True)]
        },
        string='Payments Lines')
    line_ids = fields.One2many(
        comodel_name='account.payment.order.line',
        inverse_name='payment_order_id',
        string='Payment Lines')
    income_line_ids = fields.One2many(
        comodel_name='account.payment.order.line',
        inverse_name='payment_order_id',
        states={
            'cancel': [('readonly', True)],
            'posted': [('readonly', True)]
        },
        string='Credits',
        domain=[('type', '=', 'income')],
        context={'default_type': 'income'})
    debt_line_ids = fields.One2many(
        comodel_name='account.payment.order.line',
        inverse_name='payment_order_id',
        states={
            'cancel': [('readonly', True)],
            'posted': [('readonly', True)]
        },
        string='Debits',
        domain=[('type', '=', 'debt')],
        context={'default_type': 'debt'})
    payment_rate_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Payment Rate Currency',
        states={
            'cancel': [('readonly', True)],
            'posted': [('readonly', True)]
        },
        default=lambda s: s._get_payment_rate_currency(),
        required=True)
    payment_rate = fields.Float(
        string='Exchange Rate',
        digits=(12, 6), required=True,
        states={
            'cancel': [('readonly', True)],
            'posted': [('readonly', True)]
        },
        default=1.0,
        help='The specific rate that will be used, in \
        this voucher, between the selected currency \
        (in \'Payment Rate Currency\' field)  and the \
        voucher currency.')
    paid_amount_in_company_currency = fields.Float(
        string='Paid Amount in Company Currency',
        compute='_paid_amount_in_company_currency',
        readonly=True)
    is_multi_currency = fields.Boolean(
        string='Multi Currency Voucher',
        help='Fields with internal purpose \
        only that depicts if the voucher is \
        a multi currency one or not')
    invoice_ids = fields.Many2many(
        comodel_name='account.invoice',
        compute='_get_invoice_ids',
        string='Invoices', readonly=True)

    period_id = fields.Many2one(
        string="Period", comodel_name="date.period",
        compute='_compute_period', store=True, required=False)

    @api.depends('date')
    def _compute_period(self):
        for rec in self:
            if not rec.date:
                continue
            period_obj = rec.env['date.period']
            period_date = datetime.strptime(
                rec.date, '%Y-%m-%d').date()
            period = period_obj._get_period(period_date)
            rec.period_id = period.id

    @api.depends('income_line_ids.invoice_id', 'debt_line_ids.invoice_id')
    def _get_invoice_ids(self):
        for payment in self:
            income_invs = payment.income_line_ids.mapped('invoice_id')
            debt_invs = payment.debt_line_ids.mapped('invoice_id')
            payment.invoice_ids = income_invs + debt_invs

    @api.depends('journal_id', 'company_id')
    def _get_journal_currency(self):
        for payment in self:
            payment.currency_id = payment.journal_id.currency_id or \
                payment.company_id.currency_id

    @api.model
    def _get_default_company(self):
        company = self.env['res.company']._company_default_get(
            'account.payment.order')
        return company

    @api.model
    def _get_journal(self):
        res = False
        ttype = self.env.context.get('type', 'bank')
        company = self._get_default_company()

        # Pago inmediato, al contado, desde el boton de la factura
        immediate = self.env.context.get('immediate_payment', False)

        if not immediate and ttype in ('payment', 'receipt'):
            rec = self.env['account.journal'].search([
                ('type', '=', ttype),
                ('company_id', '=', company.id)], limit=1,
                order='priority')
            if not rec:
                action = self.env.ref('account.action_account_journal_form')
                msg = ('Cannot find a Payment/Receipt journal. \
                  \nPlease create at least one.')
                raise RedirectWarning(
                  msg, action.id, _('Go to the journal configuration'))
            res = rec[0] or False
        return res and res.id

    @api.depends('debt_line_ids', 'income_line_ids', 'amount')
    def _get_writeoff_amount(self):
        for po in self:
            writeoff_amount = po._get_writeoff_amount_hook()
            currency = po.currency_id or po.company_id.currency_id
            po.writeoff_amount = currency.round(writeoff_amount)

    @api.multi
    def _get_writeoff_amount_hook(self):
        self.ensure_one
        debit = credit = 0.0
        sign = self.type == 'payment' and -1 or 1
        for l in self.debt_line_ids:
            debit += l.amount
        for l in self.income_line_ids:
            credit += l.amount
        amount = self.amount - sign * (credit - debit)
        return amount

    @api.model
    def _get_partner(self):
        return self.env.context.get('partner_id', False)

    @api.model
    def _get_reference(self):
        return self.env.context.get('reference', False)

    @api.model
    def _get_narration(self):
        return self.env.context.get('narration', False)

    @api.model
    def _get_amount(self):
        return self.env.context.get('amount', 0.0)

    @api.model
    def _get_type(self):
        return self.env.context.get('type', False)

    @api.model
    def _get_payment_rate_currency(self):
        """
          Return the default value for field payment_rate_currency_id:
            the currency of the journal
          if there is one, otherwise the currency of the user's company
        """
        journal_obj = self.env['account.journal']
        journal_id = self.env.context.get('journal_id', False)
        if journal_id:
            journal = journal_obj.browse(journal_id)
            if journal.currency:
                return journal.currency
        # No journal given in the context, use company currency as default
        return self.env.user.company_id.currency_id

    @api.depends('amount')
    def _paid_amount_in_company_currency(self):
        for p in self:
            payment = self.with_context({'date': p.date})
            self.paid_amount_in_company_currency = \
                payment.currency_id.compute(
                    payment.amount,
                    payment.company_id.currency_id)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.journal_id.type in ('sale', 'sale_refund'):
            account_id = self.partner_id.property_account_receivable_id
        elif self.journal_id.type in \
                ('purchase', 'purchase_refund', 'expense'):
            account_id = self.partner_id.property_account_payable_id
        elif self.type in ('sale', 'receipt'):
            account_id = self.journal_id.default_debit_account_id
        elif self.type in ('purchase', 'payment'):
            account_id = self.journal_id.default_credit_account_id
        else:
            account_id = self.journal_id.default_credit_account_id or \
                self.journal_id.default_debit_account_id
        self.account_id = account_id

    @api.multi
    def get_payment_lines_amount(self):
        return sum(self.payment_mode_line_ids.mapped('amount'))

    @api.multi
    def payment_order_amount_hook(self):
        amount = self.get_payment_lines_amount()
        return amount

    @api.onchange('payment_mode_line_ids')
    def onchange_payment_line(self):
        amount = self.payment_order_amount_hook()
        self.amount = amount

    @api.onchange('debt_line_ids')
    def onchange_debt_lines(self):
        self.recompute_payment_lines('debt_line_ids')

    @api.onchange('income_line_ids')
    def onchange_income_lines(self):
        self.recompute_payment_lines('income_line_ids')

    @api.multi
    def unlink(self):
        if self.state not in ['draft', 'cancel']:
            raise ValidationError(
                _("Error!\nYou can't unlink a posted payment order.\n" +
                  "First you should unreconcile It."))
        super(AccountPaymentOrder, self).unlink()

    @api.multi
    def _check_partner_set(self):
        if not self.partner_id:
            raise UserError(
                _("Error!\n" +
                  "The Partner must be set to gather accounting information."))

    @api.multi
    def update_o2m(self, field_str, lines):
        if not hasattr(self, field_str) or not lines:
            return False
        old_lines = getattr(self, field_str)
        new_lines = [x for x in lines if x['move_line_id'] not in
                     old_lines.mapped('move_line_id.id')]
        setattr(self, field_str, [(0, 0, x) for x in new_lines])
        return True

    @api.multi
    def gather_income_lines(self):
        self.ensure_one()
        self._check_partner_set()
        move_line_obj = self.env['account.move.line']
        lines_type = 'income'
        account_type = self.type == 'payment' and 'payable' or 'receivable'
        moves = move_line_obj.search([
            ('debit', '!=', 0),
            ('credit', '=', 0),
            ('account_id.internal_type', '=', account_type),
            ('reconciled', '=', False),
            ('partner_id', '=', self.partner_id.id)])
        lines = self._prepare_income_debt_lines(lines_type, moves)
        return self.update_o2m('income_line_ids', lines)

    @api.multi
    def gather_debt_lines(self):
        self.ensure_one()
        self._check_partner_set()
        move_line_obj = self.env['account.move.line']
        lines_type = 'debt'
        account_type = self.type == 'payment' and 'payable' or 'receivable'
        moves = move_line_obj.search([
            ('debit', '=', 0),
            ('credit', '!=', 0),
            ('account_id.internal_type', '=', account_type),
            ('reconciled', '=', False),
            ('partner_id', '=', self.partner_id.id)])
        lines = self._prepare_income_debt_lines(lines_type, moves)
        return self.update_o2m('debt_line_ids', lines)

    @api.multi
    def doesnt_have_residual(self, move_line):
        if move_line.reconciled:
            if self.currency_id == move_line.currency_id:
                if move_line.amount_residual_currency <= 0:
                    return True
            else:
                if move_line.amount_residual <= 0:
                    return True
        return False

    @api.multi
    def _prepare_income_debt_lines(self, lines_type, move_lines):
        res = []
        for line in move_lines:
            line_data = {}
            if self.doesnt_have_residual(line):
                continue

            amount_original = line.debit or line.credit or 0.0
            sign = lines_type == 'debt' and -1 or 1
            amount_unreconciled = sign * line.amount_residual or 0.0

            line_data = {
                'name': line.move_id.name,
                'invoice_id': line.invoice_id.id,
                'move_line_id': line.id,
                'account_id': line.account_id.id,
                'amount_original': amount_original,
                'date_original': line.date,
                'date_due': line.date_maturity,
                'amount_unreconciled': amount_unreconciled,
                'currency_id': self.currency_id.id,
                'type': lines_type,
            }
            res.append(line_data)
        return res

    @api.multi
    def recompute_payment_lines(self, onchange_attr):
        move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']

        ttype = self.env.context.get('type', 'bank')
        total_credit = total_debit = 0.0
        if ttype == 'payment':
            account_type = 'payable'
            total_debit = self.amount or 0.0
        else:
            total_credit = self.amount or 0.0
            account_type = 'receivable'

        line_ids = getattr(self, onchange_attr)
        the_line = False
        if line_ids:
            for line in line_ids:
                if line.invoice_id and not \
                        line.move_line_id and not \
                        line.account_id:
                    the_line = line
        if not the_line:
            return
        line_ids = the_line
        if not self.env.context.get('move_line_ids', False):
            ids = move_line_obj.search([
                ('account_id.internal_type', '=', account_type),
                ('reconciled', '=', False),
                ('partner_id', '=', self.partner_id.id),
                ('invoice_id', '=', line_ids.invoice_id.id)])
        else:
            return

        company_currency = self.journal_id.company_id.currency_id
        invoice_id = self.env.context.get('invoice_id', False)
        account_move_lines = ids.sorted(key=lambda x: -1 * x.id)
        move_lines_found = []

        for line in account_move_lines:
            if self.doesnt_have_residual(line):
                continue

            if invoice_id:
                if line.invoice_id.id == line_ids.invoice_id.id:
                    # if the invoice linked to the voucher
                    # line is equal to the invoice_id in context
                    # then we assign the amount on that line,
                    # whatever the other voucher lines
                    move_lines_found.append(line.id)
            elif self.currency_id == company_currency:
                # otherwise treatments is the same but with other field names
                if line.amount_residual == self.amount:
                    # if the amount residual is equal the amount
                    # voucher, we assign it to that voucher line,
                    # whatever the other voucher lines
                    move_lines_found.append(line.id)
                    break
                # otherwise we will split the voucher amount
                # on each line (by most old first)
                total_credit += line.credit and line.amount_residual or 0.0
                total_debit += line.debit and line.amount_residual or 0.0
            elif self.currency_id == line.currency_id:
                if line.amount_residual_currency == self.amount:
                    move_lines_found.append(line.id)
                    break
                line_residual = currency_obj.compute(
                    company_currency, self.currency_id,
                    abs(line.amount_residual))

                total_credit += line.credit and line_residual or 0.0
                total_debit += line.debit and line_residual or 0.0

        # voucher line creation
        res = self._prepare_income_debt_lines(
            onchange_attr == 'debt_line_ids' and 'debt' or 'income',
            account_move_lines)

        if res:
            old_lines = getattr(self, onchange_attr)
            setattr(self, onchange_attr, [(0, 0, x) for x in res])
            setattr(self, onchange_attr, getattr(
                self, onchange_attr) + old_lines)
            setattr(self, onchange_attr, getattr(
                self, onchange_attr) - line_ids)
        else:
            setattr(self, onchange_attr, False)

    def _compute_writeoff_amount(
        self, records, amount,
            type, old_writeoff):
        debit = credit = 0.0
        sign = type == 'payment' and -1 or 1
        for l in records:
            if isinstance(l, dict):
                credit += l['amount']
        return (amount - sign * (credit - debit)) + old_writeoff

    @api.multi
    def _clean_payment_lines(self):
        for payment_line in self.payment_mode_line_ids:
            if payment_line.amount == 0:
                payment_line.unlink()
        return True

    @api.multi
    def proforma_voucher(self):
        self.ensure_one()
        # Chequeamos si la writeoff_amount no es negativa
        if round(self.writeoff_amount, 2) < 0.0:
            raise ValidationError(
                _('Error!\n Cannot validate a ' +
                    'voucher with negative amount.\n Please check ' +
                    'that Writeoff Amount is not negative.'))
        if self.amount == 0.0 and not self._get_income_amount():
            raise ValidationError(
                _("Validate Error!\n") +

                _("You cannot validate a voucher with amount of 0.0") +
                _(" and no income lines"))

        self._clean_payment_lines()
        self.action_move_line_create()

        return True

    @api.multi
    def _get_income_amount(self):
        self.ensure_one()
        return sum(self.income_line_ids.mapped('amount'))

    @api.multi
    def _get_company_currency(self):
        '''
        Get the currency of the actual company.

        :param voucher_id: Id of the voucher what
          i want to obtain company currency.
        :return: currency id of the company of the voucher
        :rtype: int
        '''
        return self.journal_id.company_id.currency_id

    @api.multi
    def _get_current_currency(self):
        '''
        Get the currency of the voucher.

        :param voucher_id: Id of the voucher what
          i want to obtain current currency.
        :return: currency id of the voucher
        :rtype: int
        '''
        return self.currency_id or self._get_company_currency()

    @api.multi
    def account_move_get(self):
        '''
        This method prepare the creation of the
        account move related to the given voucher.

        :param voucher_id: Id of voucher for which
         we are creating account_move.
        :return: mapping between fieldname and value of account move to create
        :rtype: dict
        '''

        if self.number:
            name = self.number
        elif self.journal_id.sequence_id:
            if not self.journal_id.sequence_id.active:
                raise UserError(
                    _('Configuration Error !\n' +
                        'Please activate the sequence of selected journal !'))

            name = self.journal_id.sequence_id.next_by_id()
        else:
            raise UserError(
                _('Error!\n' +
                    'Please define a sequence on the journal.'))
        if not self.reference:
            ref = name.replace('/', '')
        else:
            ref = self.reference

        move = {
            'name': name,
            'journal_id': self.journal_id.id,
            'narration': self.narration,
            'date': self.date,
            'ref': ref,
        }
        return move

    @api.multi
    def create_move_line_hook(self, move_id, move_lines):
        return move_lines

    @api.model
    def _convert_paid_amount_in_company_currency(self, amount):
        res = {}
        currency = self.currency_id.with_context({'date': self.date})
        company_currency = self.company_id.currency_id
        res = currency.compute(amount, company_currency)
        return res

    @api.multi
    def _create_move_line_payment(self, move_id, name, journal_id, amount,
                                  company_currency, current_currency, sign):

        amount_in_company_currency = self.\
            _convert_paid_amount_in_company_currency(amount)
        debit = credit = 0.0
        pl_account_id = journal_id.default_debit_account_id.id
        if self.type in ('purchase', 'payment'):
            credit = amount_in_company_currency
        elif self.type in ('sale', 'receipt'):
            debit = amount_in_company_currency
        if debit < 0:
            credit = -debit
            debit = 0.0
        if credit < 0:
            debit = -credit
            credit = 0.0
        sign = debit - credit < 0 and -1 or 1
        move_line = {
            'name': name or '/',
            'debit': debit,
            'credit': credit,
            'account_id': pl_account_id,
            'move_id': move_id,
            'journal_id': self.journal_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': company_currency != current_currency and
            current_currency.id or False,
            'amount_currency': company_currency != current_currency and
            sign * amount or 0.0,
            'date': self.date,
            'date_maturity': self.date_due
        }

        return move_line

    @api.multi
    def create_move_lines(self, move_id, company_currency, current_currency):
        total_debit = total_credit = 0.0
        # TODO: is there any other alternative then the voucher type ??
        # ANSWER: We can have payment and receipt "In Advance".
        # TODO: Make this logic available.
        # -for sale, purchase we have but for the payment and receipt we do not have as based on the bank/cash journal we can not know its payment or receipt  # noqa
        if self.type in ('purchase', 'payment'):
            total_credit = self.paid_amount_in_company_currency
        elif self.type in ('sale', 'receipt'):
            total_debit = self.paid_amount_in_company_currency
        if total_debit < 0:
            total_credit = - total_debit
            total_debit = 0.0
        if total_credit < 0:
            total_debit = -total_credit
            total_credit = 0.0
        sign = total_debit - total_credit < 0 and -1 or 1

        # Creamos una move_line por payment_line
        move_lines = []
        for pml in self.payment_mode_line_ids:
            if pml.amount == 0.0:
                continue

            move_line = self._create_move_line_payment(
                move_id, pml.name, pml.payment_mode_id,
                pml.amount, company_currency,
                current_currency, sign)

            move_lines.append(move_line)

        # Si es pago contado
        # TODO
        # if self.journal_id.type not in ('receipt', 'payment'):
        #     move_line = self._create_move_line_payment(
        #         move_id, _('Immediate'),
        #         self.account_id,
        #         self.amount, company_currency,
        #         current_currency, sign)
        #
        #     move_lines.append(move_line)

        # Creamos un hook para agregar los demas asientos contables de otros modulos  # noqa
        move_lines = self.create_move_line_hook(move_id, move_lines)
        # Recorremos las lineas para  hacer un chequeo de debit y credit contra total_debit y total_credit  # noqa
        amount_credit = 0.0
        amount_debit = 0.0
        for line in move_lines:
            amount_credit += line['credit']
            amount_debit += line['debit']

        if round(amount_credit, 3) != round(total_credit, 3) or \
                round(amount_debit, 3) != round(total_debit, 3):
            if self.type in ('purchase', 'payment'):
                amount_credit -= amount_debit
                amount_debit -= amount_debit
            else:
                amount_debit -= amount_credit
                amount_credit -= amount_credit
            if round(amount_credit, 3) != round(total_credit, 3) or \
                    round(amount_debit, 3) != round(total_debit, 3):
                raise UserError(_('Voucher Error!\n\
                    Voucher Paid Amount and sum of different payment \
                        mode must be equal'))

        return move_lines

    @api.multi
    def first_move_line_get(self, move_id, company_currency, current_currency):
        """
        Return a dict to be use to create the
        first account move line of given voucher.

        :param voucher_id: Id of voucher what we are creating account_move.
        :param move_id: Id of account move where this line will be added.
        :param company_currency: id of currency of the
         company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: mapping between fieldname and
         value of account move line to create
        :rtype: dict
        """
        debit = credit = 0.0
        # TODO: is there any other alternative then the voucher type ??
        # ANSWER: We can have payment and receipt "In Advance".
        # TODO: Make this logic available.
        # -for sale, purchase we have but for the payment and
        # receipt we do not have as based on the bank/cash
        # journal we can not know its payment or receipt
        if self.type in ('purchase', 'payment'):
            credit = self.paid_amount_in_company_currency
        elif self.type in ('sale', 'receipt'):
            debit = self.paid_amount_in_company_currency
        if debit < 0:
            credit = -debit
            debit = 0.0
        if credit < 0:
            debit = -credit
            credit = 0.0
        sign = debit - credit < 0 and -1 or 1
        # set the first line of the voucher
        move_line = {
                'name': self.name or '/',
                'debit': debit,
                'credit': credit,
                'account_id': self.account_id.id,
                'move_id': move_id,
                'journal_id': self.journal_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': company_currency != current_currency and
                current_currency.id or False,
                'amount_currency': (sign * abs(self.amount)
                                    if company_currency !=
                                     current_currency else 0.0),
                'date': self.date,
                'date_maturity': self.date_due
            }
        return move_line

    @api.multi
    def _convert_amount(self, amount):
        return self.currency_id.compute(amount, self.company_id.currency_id)

    @api.multi
    def _get_exchange_lines(self, line, move_id, amount_residual,
                            company_currency, current_currency):
        if amount_residual > 0:
            account_id = line.payment_order_id.company_id.\
                expense_currency_exchange_account_id
            if not account_id:
                action_id = self.env.ref('account.action_account_form').id
                msg = _("You should configure the 'Loss Exchange Rate " +
                        "Account' to manage automatically the booking of " +
                        "accounting entries related to differences " +
                        "between exchange rates.")
                raise RedirectWarning(
                    msg, action_id, _('Go to the configuration panel'))
        else:
            account_id = line.payment_order_id.company_id.\
                income_currency_exchange_account_id
            if not account_id:
                action_id = self.env.ref('account.action_account_form').id
                msg = _("You should configure the 'Gain Exchange Rate " +
                        "Account' to manage automatically the booking of " +
                        "accounting entries related to differences " +
                        "between exchange rates.")
                raise RedirectWarning(
                    msg, action_id, _('Go to the configuration panel'))
        # Even if the amount_currency is never filled, we need to pass the foreign currency because otherwise  # noqa
        # the receivable/payable account may have a secondary currency, which render this field mandatory  # noqa
        if line.account_id.currency_id:
            account_currency_id = line.account_id.currency_id
        else:
            account_currency_id = company_currency != current_currency and \
                current_currency or False
        move_line = {
            'journal_id': line.payment_order_id.journal_id.id,
            'name': _('change')+': '+(line.name or '/'),
            'account_id': line.account_id.id,
            'move_id': move_id,
            'partner_id': line.payment_order_id.partner_id.id,
            'currency_id': account_currency_id.id,
            'amount_currency': 0.0,
            'quantity': 1,
            'credit': amount_residual > 0 and amount_residual or 0.0,
            'debit': amount_residual < 0 and -amount_residual or 0.0,
            'date': line.payment_order_id.date,
        }
        move_line_counterpart = {
            'journal_id': line.payment_order_id.journal_id.id,
            'name': _('change')+': '+(line.name or '/'),
            'account_id': account_id.id,
            'move_id': move_id,
            'amount_currency': 0.0,
            'partner_id': line.payment_order_id.partner_id.id,
            'currency_id': account_currency_id.id,
            'quantity': 1,
            'debit': amount_residual > 0 and amount_residual or 0.0,
            'credit': amount_residual < 0 and -amount_residual or 0.0,
            'date': line.payment_order_id.date,
        }
        return (move_line, move_line_counterpart)

    @api.multi
    def voucher_move_line_create(self, line_total, move_id,
                                 company_currency, current_currency):
        move_line_obj = self.env['account.move.line']
        tot_line = line_total
        rec_lst_ids = []

        date = self.read(['date'])[0]['date']
        self = self.with_context({'date': date})
        # voucher_currency = self.journal_id.currency_id or self.company_id.currency_id  # noqa
        prec = self.env['decimal.precision'].precision_get('account')
        for line in self.line_ids:
            if not line.amount and not \
                    (line.move_line_id and not float_compare(
                        line.move_line_id.debit,
                        line.move_line_id.credit,
                        precision_digits=prec) and not
                        float_compare(
                            line.move_line_id.debit, 0.0,
                            precision_digits=prec)):
                continue
            sign = line.type == 'debt' and -1 or 1
            amount = sign * self._convert_amount(
                line.untax_amount or line.amount)
            if line.amount == line.amount_unreconciled:
                if not line.move_line_id:
                    raise UserError(_("Wrong voucher line\n\
                        The invoice you are willing to \
                        pay is not valid anymore."))
                currency_rate_difference = (
                    line.move_line_id.amount_residual - amount)
            else:
                currency_rate_difference = 0.0
            move_line_analytic_account_id = line.account_analytic_id and \
                line.account_analytic_id.id or False
            move_line = {
                'journal_id': self.journal_id.id,
                'name': line.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id != company_currency and
                self.currency_id.id or False,
                'analytic_account_id': move_line_analytic_account_id,
                'quantity': 1,
                'credit': 0.0,
                'debit': 0.0,
                'date': self.date
            }
            if amount < 0:
                amount = -amount

            if (line.type == 'debt'):
                tot_line += amount
                move_line['debit'] = amount
            else:
                tot_line -= amount
                move_line['credit'] = amount

            if self.tax_id and self.type in ('sale', 'purchase'):
                move_line.update({
                    'account_tax_id': self.tax_id.id,
                })

            # compute the amount in foreign currency
            foreign_currency_diff = 0.0
            amount_currency = False
            if line.move_line_id:
                # We want to set it on the account move line as soon as the original line had a foreign currency  # noqa
                if line.move_line_id.currency_id and \
                        line.move_line_id.currency_id != company_currency:
                    # we compute the amount in that foreign currency.
                    if line.move_line_id.currency_id == current_currency:
                        sign = (move_line['debit'] -
                                move_line['credit']) < 0 and -1 or 1
                        amount_currency = sign * (line.amount)
                    else:
                        amount_currency = line.move_line_id.currency_id.\
                            compute(move_line['debit']-move_line['credit'],
                                    company_currency)
                if line.amount == line.amount_unreconciled:
                    foreign_currency_diff = \
                        line.move_line_id.amount_residual_currency - \
                        abs(amount_currency)

            move_line['amount_currency'] = amount_currency
            payment_line = move_line_obj.create(move_line)
            new_amls = payment_line + line.move_line_id

            if not self.company_id.currency_id.is_zero(
                    currency_rate_difference):
                # Change difference entry in company currency
                exch_lines = self._get_exchange_lines(
                    line, move_id, currency_rate_difference,
                    company_currency, current_currency)
                new_aml = move_line_obj.create(exch_lines[0])
                move_line_obj.create(exch_lines[1])
                new_amls += new_aml

            if line.move_line_id and line.move_line_id.currency_id and \
                    not line.move_line_id.currency_id.is_zero(
                        foreign_currency_diff):
                # Change difference entry in voucher currency
                move_line_foreign_currency = {
                    'journal_id': line.payment_order_id.journal_id.id,
                    'name': _('change')+': '+(line.name or '/'),
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'partner_id': line.payment_order_id.partner_id.id,
                    'currency_id': line.move_line_id.currency_id.id,
                    'amount_currency': (-1 if line.type == 'cr' else 1) *
                    foreign_currency_diff,
                    'quantity': 1,
                    'credit': 0.0,
                    'debit': 0.0,
                    'date': line.payment_order_id.date,
                }
                new_aml = move_line_obj.create(move_line_foreign_currency)
                new_amls += new_aml
            if line.move_line_id.id:
                rec_lst_ids.append(new_amls)
        return (tot_line, rec_lst_ids)

    @api.multi
    def writeoff_move_line_get(self, line_total, move_id, name,
                               company_currency, current_currency):
        move_line = {}

        current_currency_obj = self.currency_id or \
            self.journal_id.company_id.currency_id

        if not current_currency_obj.is_zero(line_total):
            diff = line_total
            account_id = False
            write_off_name = ''
            if self.payment_option == 'with_writeoff':
                account_id = self.writeoff_acc_id.id
                write_off_name = self.comment
            elif self.partner_id:
                if self.type in ('sale', 'receipt'):
                    account_id = self.partner_id.\
                        property_account_receivable_id.id
                else:
                    account_id = self.partner_id.property_account_payable_id.id
            else:
                # fallback on account of voucher
                account_id = self.account_id.id
            sign = self.type == 'payment' and -1 or 1
            move_line = {
                'name': write_off_name or name,
                'account_id': account_id,
                'move_id': move_id,
                'partner_id': self.partner_id.id,
                'date': self.date,
                'credit': diff > 0 and diff or 0.0,
                'debit': diff < 0 and -diff or 0.0,
                'amount_currency': company_currency != current_currency and
                (sign * -1 * self.writeoff_amount) or 0.0,
                'currency_id': company_currency != current_currency and
                current_currency.id or False,
                'analytic_account_id': self.analytic_id and
                self.analytic_id.id or False,
            }

        return move_line

    @api.multi
    def action_move_line_create(self):
        '''
        Confirm the vouchers given in ids and create
        the journal entries for each of them
        '''
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        for payment in self:
            if payment.move_id:
                continue
            company_currency = payment._get_company_currency()
            current_currency = payment._get_current_currency()
            # But for the operations made by _convert_amount, we always need to give the date in the context  # noqa
            ctx = {
                'date': payment.date,
                'check_move_validity': False,
            }
            # Create the account move record.
            move_recordset = move_obj.with_context(ctx).create(
                payment.account_move_get())
            # Get the name of the account_move just created
            name = move_recordset.name
            move_id = move_recordset.id

            if payment.type in ('payment', 'receipt'):
                # Creamos las lineas contables de todas las formas de pago, etc  # noqa
                move_line_vals = self.create_move_lines(
                    move_id, company_currency, current_currency)
                line_total = 0.0
                for vals in move_line_vals:
                    line_total += vals['debit'] - vals['credit']
                    move_line_obj.with_context(ctx).create(vals)
            else:
                # Create the first line of the voucher
                move_line_brw = move_line_obj.with_context(ctx).create(
                    self.first_move_line_get(
                        move_id, company_currency,
                        current_currency))
                line_total = move_line_brw.debit - move_line_brw.credit

            rec_list_ids = []
            if payment.type == 'sale':
                line_total = line_total - self._convert_amount(
                    payment.tax_amount, payment.id)
            elif payment.type == 'purchase':
                line_total = line_total + self._convert_amount(
                    payment.tax_amount, payment.id)
            # Create one move line per voucher line where amount is not 0.0
            line_total, rec_list_ids = self.with_context(
                ctx).voucher_move_line_create(
                    line_total, move_id, company_currency, current_currency)

            # Create the writeoff line if needed
            ml_writeoff = self.writeoff_move_line_get(
                line_total, move_id, name, company_currency, current_currency)
            if ml_writeoff:
                move_line_obj.with_context(ctx).create(ml_writeoff)

            # We post the voucher.
            self.write({
                'move_id': move_id,
                'state': 'posted',
                'number': name,
            })

            move_recordset.post()
            # We automatically reconcile the account move lines.
            for move_lines in rec_list_ids:
                if len(move_lines) >= 2:
                    move_lines.reconcile(
                        writeoff_acc_id=payment.writeoff_acc_id.id,
                        writeoff_journal_id=payment.journal_id.id)

            # Borramos las lineas que estan en 0
            for line in payment.line_ids:
                if not line.amount:
                    line.unlink()

        return True

    @api.multi
    def cancel_voucher(self):
        for payment in self:
            if payment.move_id:
                payment.move_id.line_ids.remove_move_reconcile()
                payment.move_id.button_cancel()
                payment.move_id.unlink()
        self.write({
            'state': 'cancel',
            'move_id': False,
        })
        return True

    @api.multi
    def action_cancel_draft(self):
        self.write({'state': 'draft'})
        return True


class AccountPaymentOrderLine(models.Model):
    _name = 'account.payment.order.line'
    _description = 'Voucher Lines'
    _order = "move_line_id"

    payment_order_id = fields.Many2one(
        comodel_name='account.payment.order', string='Payment Order',
        ondelete='cascade')
    name = fields.Char(string='Description', default='')
    account_id = fields.Many2one(
        comodel_name='account.account', string='Account')
    partner_id = fields.Many2one(
        comodel_name='res.partner', string='Partner',
        related='payment_order_id.partner_id')
    untax_amount = fields.Float(string='Untax Amount')
    amount = fields.Float(string='Amount', digits=dp.get_precision('Account'))
    reconcile = fields.Boolean(string='Full Reconcile')
    type = fields.Selection(
        string='Dr/Cr', selection=[
            ('debt', 'Debt'),
            ('income', 'Income')])
    move_line_id = fields.Many2one(
        comodel_name='account.move.line',
        string='Journal Item', copy=False)
    date_original = fields.Date(
        string='Date', related='move_line_id.date', readonly=True)
    account_analytic_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account')
    date_due = fields.Date(
        string='Due Date', related='move_line_id.date_maturity', readonly=True)
    amount_original = fields.Float(
        string='Original Amount', digits=dp.get_precision('Account'),
        compute='_compute_balance', store=True)
    amount_unreconciled = fields.Float(
        string='Open Balance', digits=dp.get_precision('Account'),
        compute='_compute_balance', store=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company',
        related='payment_order_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(
        comodel_name='res.currency', string='Currency',
        compute='_compute_currency_id', readonly=True)
    invoice_id = fields.Many2one(
        comodel_name='account.invoice', string='Invoice',
        domain=[('state', '=', 'open')])
    move_invoice_id = fields.Many2one(
        comodel_name='account.invoice', related='move_line_id.invoice_id')
    ref = fields.Char(string='Reference', size=64)
    state = fields.Selection(
        string='State', related='payment_order_id.state', readonly=True)

    @api.depends('move_line_id')
    def _compute_balance(self):
        for line in self:
            move_line = line.move_line_id
            line.amount_original = move_line.debit or move_line.credit or 0.0
            sign = line.type == 'debt' and -1 or 1
            line.amount_unreconciled = sign * move_line.amount_residual or 0.0

    @api.multi
    def _compute_currency_id(self):
        for line in self:
            if line.payment_order_id:
                line.currency_id = line.payment_order_id.currency_id

    @api.onchange('reconcile')
    def amount_full_conciliation(self):
        for line in self:
            if line.amount_unreconciled == line.amount:
                line.amount = 0
            else:
                line.amount = line.amount_unreconciled

    def _check_amount_over_original(self):
        if not (0 <= self.amount <= self.amount_unreconciled):
            print(self.amount, self.amount_unreconciled)
            raise ValidationError(
                _("Error!\nThe amount assigned to an invoice must not excede" +
                  " the unreconciled amount, nor be negative."))

    @api.constrains('amount')
    def _check_amount(self):
        for order_line in self:
            order_line._check_amount_over_original()

    @api.onchange('amount')
    def onchange_amount(self):
        self._check_amount_over_original()

    @api.multi
    def _compute_writeoff_amount(
        self, debt_line_ids, income_line_ids,
            amount, type, old_writeoff):
        debit = credit = 0.0
        sign = type == 'payment' and -1 or 1
        for l in debt_line_ids:
            if isinstance(l, dict):
                debit += l['amount']
        for l in income_line_ids:
            if isinstance(l, dict):
                credit += l['amount']
        return (amount - sign * (credit - debit)) + old_writeoff


class AccountPaymentModeLine(models.Model):
    _name = 'account.payment.mode.line'
    _description = 'Payment method lines'

    name = fields.Text(
        help='Payment reference', string='Description')
    payment_order_id = fields.Many2one(
        comodel_name='account.payment.order', string='Payment Order')
    payment_mode_id = fields.Many2one(
        comodel_name='account.journal', string='Payment Method')
    amount = fields.Float(
        string='Amount', digits=(16, 2), default=0.0, required=False,
        help='Payment amount in the company currency')
    amount_currency = fields.Float(
        string='Amount in Partner Currency',
        digits=(16, 2), required=False,
        help='Payment amount in the partner currency')
    currency_id = fields.Many2one(
        comodel_name='res.currency', compute='_compute_currency',
        string='Currency')
    company_currency = fields.Many2one(
        comodel_name='res.currency', string='Company Currency',
        readonly=True, default=lambda s: s._get_company_currency())
    date = fields.Date(
        string='Payment Date', help="This date is informative only.")

    @api.depends('payment_mode_id')
    def _compute_currency(self):
        for i in self:
            i.currency_id = i.payment_mode_id.currency_id or \
                self._get_company_currency()

    @api.model
    def _get_company_currency(self):
        currency_obj = self.env['res.currency']
        if self.env.user.company_id:
            return self.env.user.company_id.currency_id
        else:
            return currency_obj.search([('rate', '=', 1.0)], limit=1)


class DatePeriod(models.Model):
    _name = 'date.period'
    _inherit = 'date.period'

    @api.multi
    def _hook_affected_models(self, affected_models):
        affected_models.append('account.payment.order')
        return super()._hook_affected_models(affected_models)
