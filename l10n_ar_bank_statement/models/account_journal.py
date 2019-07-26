##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def detach_statement_lines(self):
        return self.type in ("bank", "cash")

    def _build_open_statement_search_domain(self, journal_id=False):
        domain = [("state", "=", "open")]

        if journal_id:
            domain.append(("journal_id", "=", journal_id))
        else:
            domain.append(("journal_id.type", "=", "cash"))

        return domain

    def find_open_statement_id(self, journal_id=False):
        statement_domain = self._build_open_statement_search_domain(journal_id)
        return self.env["account.bank.statement"].search(
            statement_domain,
            order="create_date",
            limit=1,
        ).id
