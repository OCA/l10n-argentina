##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import api, fields, models


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    def _get_next_name(self):
        return self.env["ir.sequence"].next_by_code(self._name)

    @api.model
    def create(self, vals):
        if not vals.get("name", False):
            vals["name"] = self._get_next_name()

        return super(AccountBankStatement, self).create(vals)

    @api.multi
    def write(self, vals):
        if "name" in vals and not vals["name"]:
            vals["name"] = self._get_next_name()

        return super(AccountBankStatement, self).write(vals)

    @api.one
    @api.depends(
        'balance_start',
        'balance_end_real',
        'line_ids',
        'line_ids.amount',
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
        self.mapped("line_ids").open_line()
        return ret

    @api.multi
    def button_draft(self):
        ret = super(AccountBankStatement, self).button_draft()
        self.mapped("line_ids").open_line()
        return ret

    def unlink_unconfirmed_lines(self):
        unconfirmed_lines = self.mapped("line_ids").filtered(
            lambda l: l.state != "confirm")
        return unconfirmed_lines.remove_line()

    @api.multi
    def button_confirm_bank(self):
        """Extend to unrelate unconfirmed absl from the abs."""

        self.unlink_unconfirmed_lines()
        ret = super(AccountBankStatement, self).button_confirm_bank()
        return ret


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    statement_id = fields.Many2one(required=False)
    journal_id = fields.Many2one(related=False)
    company_id = fields.Many2one(related=False)
    statement_state = fields.Selection(related="statement_id.state")
    payment_id = fields.Many2one(
        'account.payment', string='Payment reference', copy=False)
    payment_order_id = fields.Many2one(
        'account.payment.order', string='Payment Order reference', copy=False)
    concept_id = fields.Many2one(
        comodel_name='pos.box.concept', string='Concept')
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
    state = fields.Selection(
        lambda l: l._get_state_select(), related=False, string='Status',
        readonly=False, default=lambda l: l._get_default_state_value())

    def open_line(self):
        return self.write({"state": "open"})

    def remove_line(self, open_lines=True):
        if open_lines:
            self.open_line()

        return self.write({"statement_id": False})

    @api.model
    def ensure_line_type(self, vals):
        """ Lines from pos does not have line_type defined, set it """
        line_type = vals.get('line_type')
        if not line_type:
            amount = vals.get('amount')
            lt = 'in' if amount > 0 else 'out'
            vals['line_type'] = lt

    @api.model
    def create(self, vals):
        journal_id = vals.get('journal_id')
        statement_id = vals.get('statement_id')
        if not vals.get('company_id'):
            if journal_id:
                company_id = self.env['account.journal'].browse(
                    journal_id).company_id.id
            else:
                company_model = self.env['res.company']
                company_id = company_model._company_default_get(
                    'account.bank.statement').id
            if company_id:
                vals['company_id'] = company_id
        # Not journal here? gather the one defined in the statement
        # Done to handle differences in cash amount
        if not journal_id and statement_id:
            touse_journal = self.env['account.bank.statement'].browse(
                statement_id).journal_id
            if touse_journal:
                vals['journal_id'] = touse_journal.id
        self.ensure_line_type(vals)
        res = super().create(vals)
        return res

    @api.multi
    def unlink(self):
        if self.env.context.get("force_unlink_statement_line", False):
            return super(AccountBankStatementLine, self).unlink()

        lines_to_unlink = self.filtered(lambda l: l.line_type in ('out', 'in'))
        (self - lines_to_unlink).remove_line()
        return super(AccountBankStatementLine, lines_to_unlink).unlink()

    def _get_state_select(self):
        return self.env["account.bank.statement"]._fields["state"].selection

    def _get_default_state_value(self):
        try:
            return self.env["account.bank.statement"].default_get(
                ["state"])["state"]
        except KeyError:
            return False

    def _filter_state_to_create_move(self, line):
        return line.line_type in ("receipt", "payment")

    def fast_counterpart_creation(self):
        wont_create_move = self.filtered(self._filter_state_to_create_move)
        return super(AccountBankStatementLine, self - wont_create_move).\
            fast_counterpart_creation()

    def confirm(self):
        return self.write({"state": "confirm"})

    @api.multi
    def button_confirm(self):
        return self.confirm()

    @api.multi
    def button_open_line(self):
        return self.open_line()
