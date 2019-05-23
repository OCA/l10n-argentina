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
