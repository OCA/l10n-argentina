##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import api, fields, models


class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    bank_statement_line_ids = fields.One2many(
        'account.bank.statement.line',
        'payment_order_id',
        string='Bank Statement Lines',
    )
    statement_count = fields.Integer(
        string='Related Bank Statement Qty.',
        compute='_calc_bank_statement_count',
    )

    def _calc_bank_statement_count_from_lines(self, bank_lines):
        ap_model = self.env['account.payment']
        return ap_model._calc_bank_statement_count_from_lines(bank_lines)

    @api.depends("bank_statement_line_ids")
    def _calc_bank_statement_count(self):
        for payment in self:
            statement_count = self._calc_bank_statement_count_from_lines(
                payment.bank_statement_line_ids,
            )
            payment.statement_count = statement_count

    def no_statement_redirect(self):
        ap_model = self.env['account.payment']
        return ap_model.no_statement_redirect()

    def create_statement_line(self, data, journal):
        ap_model = self.env['account.payment']
        return ap_model.create_statement_line(data, journal)

    @api.multi
    def proforma_voucher(self):
        ret = super(AccountPaymentOrder, self).proforma_voucher()

        for payment_order in self:
            for line in payment_order.payment_mode_line_ids:
                journal = line.payment_mode_id or payment_order.journal_id
                if not journal.detach_statement_lines():
                    continue

                self.create_statement_line(line, journal)
        return ret

    def check_confirmed_statement_lines(self):
        ap_model = self.env['account.payment']
        lines = self.mapped("bank_statement_line_ids")
        return ap_model.check_confirmed_statement_lines(lines)

    def forced_st_line_unlink(self, lines=False):
        ap_model = self.env['account.payment']
        lines = lines or self.mapped("bank_statement_line_ids")
        return ap_model.forced_st_line_unlink(lines)

    @api.multi
    def cancel_voucher(self):
        for payment_order in self:
            # Do not proceed if there
            # are account.bank.statement.line on a confirmed ABS
            if not payment_order.check_confirmed_statement_lines():
                return False

        ret = super(AccountPaymentOrder, self).cancel_voucher()
        self.forced_st_line_unlink()
        return ret

    @api.multi
    def button_open_bank_statements(self):
        bank_lines = self.mapped("bank_statement_line_ids")
        ap_model = self.env['account.payment']
        statements = ap_model._get_statements_from_lines(bank_lines)
        form = self.env.ref('account.view_bank_statement_form')
        if len(statements) == 1:
            return {
                'res_model': 'account.bank.statement',
                'src_model': 'account.bank.statement',
                'type': 'ir.actions.act_window',
                'views': [(form.id, 'form')],
                'view_id': form.id,
                'target': 'current',
                'res_id': statements.id,
                'context': str(self.env.context),
            }

        tree = self.env.ref('account.view_bank_statement_tree')
        return {
            'res_model': 'account.bank.statement',
            'src_model': 'account.bank.statement',
            'type': 'ir.actions.act_window',
            'views': [(tree.id, 'tree'), (form.id, 'form')],
            'view_id': False,
            'target': 'current',
            'res_id': statements.ids,
            'context': str(self.env.context),
        }


class AccountPaymentModeLine(models.Model):
    _inherit = 'account.payment.mode.line'

    def _build_invoices_info(self):
        """
        Show invoices name concatenated.
        """

        invoices = self.mapped("payment_order_id").mapped(
            "line_ids").mapped("invoice_id")
        return ', '.join(name or '' for _id, name in invoices.name_get())

    def _prepare_statement_line_data(self):
        payment_order = self.payment_order_id
        line_type = payment_order.type

        # Si el voucher no tiene partner, ponemos el de la compania
        partner = payment_order.partner_id or \
            payment_order.company_id.partner_id
        journal = self.payment_mode_id or payment_order.journal_id

        if payment_order.type == 'payment':
            sign = -1
            account = journal.default_debit_account_id
        else:
            sign = 1
            account = journal.default_credit_account_id

        amount = self.amount * sign
        invoices_info = self._build_invoices_info()

        st_line_data = {
            'ref': invoices_info,
            'name': self.name or payment_order.number,
            'date': self.date or payment_order.date,
            'journal_id': journal.id,
            'company_id': payment_order.company_id.id,
            'payment_order_id': payment_order.id,
            'partner_id': partner.id,
            'account_id': account.id,
            'line_type': line_type,
            'amount': amount,
            'state': 'open',
        }
        return st_line_data
