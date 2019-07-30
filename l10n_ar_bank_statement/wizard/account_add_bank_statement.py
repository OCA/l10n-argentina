##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import api, fields, models


class WizardAddAccountBankStatementLine(models.TransientModel):
    _name = "wizard.add.account.bank.statement.line"
    _description = "Wizard to link Account Bank " + \
        "Statement Lines with an Statement"

    do_confirm = fields.Boolean(
        string='Confirm all lines', default=False)
    statement_id = fields.Many2one(
        'account.bank.statement',
        string='Bank Statement',
        required=True,
        ondelete='cascade',
        default=lambda w: w._get_default_statement_id()
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        ondelete='cascade',
        default=lambda w: w._get_default_journal_id(),
    )
    statement_line_ids = fields.Many2many(
        comodel_name='account.bank.statement.line',
        relation='st_line_add_wiz_rel',
        column1='wiz_id',
        column2='line_id',
        string='Lines',
        default=lambda w: w._get_default_line_ids(),
    )

    def _get_default_statement_id(self):
        statement_id = self.env.context.get("active_id", False)
        statement = self.env["account.bank.statement"].browse(statement_id)
        return statement

    def _get_default_journal_id(self):
        statement_id = self.env.context.get("active_id", False)
        statement = self.env["account.bank.statement"].browse(statement_id)
        return statement.journal_id

    def _get_default_line_ids(self):
        statement_id = self.env.context.get("active_id", False)
        statement = self.env["account.bank.statement"].browse(statement_id)

        domain = [
            ("journal_id", "=", statement.journal_id.id),
            ("statement_id", "=", False),
            ("state", "=", "open"),
        ]

        lines = self.env["account.bank.statement.line"].search(domain)

        return [(6, False, lines.ids)]

    def add_lines(self):
        statement = self.statement_id
        ret = statement.write({
            "line_ids": [(4, line.id) for line in self.statement_line_ids],
        })

        if self.do_confirm:
            self.statement_line_ids.confirm()
        return ret

    @api.multi
    def button_add_lines(self):
        return self.add_lines()
