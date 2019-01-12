##############################################################################
#
#    Copyright (C) 2004-2010 Pexego Sistemas Informáticos. All Rights Reserved
#    Copyright (C) 2010-2014 Eynes - Ingeniería del software All Rights Reserved
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
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

from odoo import api, fields, models


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    @api.one
    @api.depends(
        'line_ids',
        'balance_start',
        'line_ids.amount',
        'balance_end_real',
        'line_ids.state',
    )
    def _end_balance(self):
        lines = self.line_ids.filtered(lambda l: l.state == "confirm")
        self.total_entry_encoding = sum(lines.mapped("amount"))
        self.balance_end = self.balance_start + self.total_entry_encoding
        self.difference = self.balance_end_real - self.balance_end

    @api.multi
    def button_open(self):
        ret = super(AccountBankStatement, self).button_open()
        self.mapped("line_ids").write({"state": "open"})
        return ret

    @api.multi
    def button_draft(self):
        ret = super(AccountBankStatement, self).button_draft()
        self.mapped("line_ids").write({"state": "open"})
        return ret

    def unlink_unconfirmed_lines(self):
        unconfirmed_lines = self.mapped("line_ids").filtered(lambda l: l.state != "confirm")
        return unconfirmed_lines.write({"statement_id": False})

    @api.multi
    def button_confirm_bank(self):
        self.unlink_unconfirmed_lines()
        ret = super(AccountBankStatement, self).button_confirm_bank()
        return ret


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    statement_id = fields.Many2one(required=False)
    journal_id = fields.Many2one(related=False)
    company_id = fields.Many2one(related=False)
    state = fields.Selection(lambda l: l._get_state_select(), related=False, string='Status',
                             readonly=False, default=lambda l: l._get_default_state_value())
    payment_id = fields.Many2one('account.payment', string='Payment reference')
    payment_order_id = fields.Many2one('account.payment.order', string='Payment Order reference')
    line_type = fields.Selection(
        [
            ("in", "Income"),
            ("out", "Expense"),
            ("receipt", "Receipt"),
            ("payment", "Payment"),
        ],
        string="Type",
        help="Type of the associated operation",
        required=True,
    )

    def _get_state_select(self):
        return self.env["account.bank.statement"]._fields["state"].selection

    def _get_default_state_value(self):
        try:
            return self.env["account.bank.statement"].default_get(["state"])["state"]
        except KeyError:
            return False

    def _filter_state_to_create_move(self, line):
        return line.line_type in ("receipt", "payment")

    def fast_counterpart_creation(self):
        wont_create_move = self.filtered(self._filter_state_to_create_move)
        return super(AccountBankStatementLine, self - wont_create_move).fast_counterpart_creation()

    def confirm(self):
        return self.write({"state": "confirm"})

    @api.multi
    def button_confirm(self):
        return self.confirm()
