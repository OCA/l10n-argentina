# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.depends("l10n_ar_afip_pos_system")
    def _compute_l10n_ar_arca_edi_enabled(self):
        res = super()._compute_l10n_ar_arca_edi_enabled()
        for journal in self:
            if journal.l10n_ar_afip_pos_system in ("FEERCEL", "FEERCELP"):
                journal.l10n_ar_arca_edi_enabled = (
                    journal.country_code == "AR" and journal.l10n_ar_is_pos
                )
        return res
