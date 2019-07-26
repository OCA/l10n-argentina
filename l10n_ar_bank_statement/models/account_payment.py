##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import _, api, exceptions, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    bank_statement_line_ids = fields.One2many(
        'account.bank.statement.line',
        'payment_id',
        string='Bank Statement Lines',
    )
    statement_count = fields.Integer(
        string='Related Bank Statement Qty.',
        compute='_calc_bank_statement_count',
    )

    def _get_statements_from_lines(self, bank_lines):
        return bank_lines.mapped("statement_id")

    def _calc_bank_statement_count_from_lines(self, bank_lines):
        statements = self._get_statements_from_lines(bank_lines)
        return len(set(statements.ids))

    @api.depends("bank_statement_line_ids")
    def _calc_bank_statement_count(self):
        for payment in self:
            statement_count = self._calc_bank_statement_count_from_lines(
                payment.bank_statement_line_ids,
            )
            payment.statement_count = statement_count

    def _build_invoices_info(self):
        """
        Show invoices name concatenated.
        """

        invoices = self.mapped("invoice_ids")
        return ', '.join(name or '' for _id, name in invoices.name_get())

    def _prepare_statement_line_data(self):
        # Si el voucher no tiene partner, ponemos el de la compania
        partner = self.partner_id or self.company_id.partner_id
        journal = self.journal_id

        if self.payment_type == 'outbound':
            sign = -1
            account = journal.default_debit_account_id
            line_type = "payment"
        else:
            sign = 1
            account = journal.default_credit_account_id
            line_type = "receipt"

        amount = self.amount * sign
        invoices_info = self._build_invoices_info()

        st_line_values = {
            'ref': invoices_info or self.communication,
            'name': self.name or self.communication,
            'date': self.payment_date,
            'journal_id': journal.id,
            'company_id': self.company_id.id,
            'payment_id': self.id,
            'partner_id': partner.id,
            'account_id': account.id,
            'line_type': line_type,
            'amount': amount,
            'state': 'open',
        }

        return st_line_values

    def no_statement_redirect(self):
        err = _("No open 'Cash' Bank Statement! " +
                "Go to the dashboard and open it")
        action_id = self.env.ref(
            "account.open_account_journal_dashboard_kanban").id
        raise exceptions.RedirectWarning(err, action_id, _("Open Dashboard"))

    def _create_statement_line(self, st_line_values):
        return self.env['account.bank.statement.line'].create(st_line_values)

    def create_statement_line(self, data, journal):
        st_line_values = data._prepare_statement_line_data()

        if journal.type == "cash":
            statement_id = journal.find_open_statement_id(journal.id)
            if not statement_id:
                return self.no_statement_redirect()

            st_line_values["statement_id"] = statement_id
            st_line_values["state"] = "confirm"

        return self._create_statement_line(st_line_values)

    @api.multi
    def post(self):
        ret = super(AccountPayment, self).post()

        for payment in self:
            payment_type = payment.payment_type
            journal = payment.journal_id
            if not journal.detach_statement_lines() or \
                    payment_type not in ("inbound", "outbound"):
                continue

            self.create_statement_line(payment, journal)

        return ret

    def check_confirmed_statement_lines(self, lines=False, raise_error=True):
        lines = lines or self.bank_statement_line_ids
        if not lines:
            return True

        for st in lines:
            if st.statement_id.state == 'confirm':
                if raise_error:
                    err = _(
                        """You can't cancel a Payment with confirmed Bank Statements

                        HINT: Click on the 'Bank Statements' button your left.
                        """
                    )
                    raise exceptions.UserError(err)
                else:
                    return False

        return True

    def forced_st_line_unlink(self, lines=False):
        # Remove account.bank.statement.line after cancel
        lines = lines or self.mapped("bank_statement_line_ids")
        return lines.with_context(force_unlink_statement_line=True).unlink()

    @api.multi
    def cancel(self):
        for payment in self:
            # Do not proceed if there are confirmed account.bank.statement.line
            if not payment.check_confirmed_statement_lines():
                return False

        ret = super(AccountPayment, self).cancel()

        self.forced_st_line_unlink()

        return ret

    @api.multi
    def button_open_bank_statements(self):
        bank_lines = self.mapped("bank_statement_line_ids")
        statements = self._get_statements_from_lines(bank_lines)
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
