##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2014 Eynes - Ingeniería del software All Rights Reserved
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models


class WizardImportAccountBankStatementLine(models.TransientModel):
    _name = "wizard.import.account.bank.statement.line"
    _description = "Wizard to link Account Bank Statement Lines with an Statement"

    do_confirm = fields.Boolean(string='Confirm all lines', default=False)
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
        relation='st_line_import_wiz_rel',
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
            #("line_type", "in", ("receipt", "payment")),
        ]

        lines = self.env["account.bank.statement.line"].search(domain)

        return [(6, False, lines.ids)]

    def add_lines(self):
        statement = self.statement_id
        ret = statement.write({"line_ids": [(4, line.id) for line in self.statement_line_ids]})

        if self.do_confirm:
            self.statement_line_ids.confirm()
            #ret = statement.check_confirm_bank()

        return ret

    @api.multi
    def button_add_lines(self):
        return self.add_lines()
