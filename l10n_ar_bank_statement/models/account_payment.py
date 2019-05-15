##############################################################################
#
#    Copyright (C) 2010-2014 Eynes - Ingeniería del software All Rights Reserved
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#    All Rights Reserved. See AUTHORS for details.
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
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
        """Show invoices name concatenated."""

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

        st_line_data = {
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
            #'creation_type': 'system',
        }

        return st_line_data

    def no_statement_redirect(self):
        err = _("No open 'Cash' Bank Statement! Go to the dashboard and open it")
        action_id = self.env.ref("account.open_account_journal_dashboard_kanban").id
        raise exceptions.RedirectWarning(err, action_id, _("Open Dashboard"))

    @api.multi
    def post(self):
        ret = super(AccountPayment, self).post()
        bank_st_line_obj = self.env['account.bank.statement.line']

        for payment in self:
            payment_type = payment.payment_type
            journal = payment.journal_id
            if not journal.detach_statement_lines() or payment_type not in ("inbound", "outbound"):
                continue

            st_line_data = payment._prepare_statement_line_data()

            if journal.type == "cash":
                statement_id = journal.find_open_statement_id()
                if not statement_id:
                    raise exceptions.RedirectWarning()

                st_line_data["statement_id"] = statement_id
                st_line_data["state"] = "confirm"

            bank_st_line_obj.create(st_line_data)

        return ret

    def check_confirmed_stament_lines(self, lines=False):
        lines = lines or self.bank_statement_line_ids
        if not lines:
            return True

        for st in lines:
            if st.state == 'confirm':
                err = _(
                    """You can't cancel a Payment with confirmed Bank Statements

                    HINT: Click on the 'Bank Statements' button your right.
                    """
                )
                raise exceptions.UserError(err)

        return True

    @api.multi
    def cancel(self):
        for payment in self:
            # Do not proceed if there are confirmed account.bank.statement.line
            if not payment.check_confirmed_stament_lines():
                return False

        ret = super(AccountPayment, self).cancel()

        # Remove account.bank.statement.line after cancel
        self.mapped("bank_statement_line_ids").unlink()

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
