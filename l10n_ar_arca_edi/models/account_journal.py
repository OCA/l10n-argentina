# Copyright 2026 Leonobitech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ar_arca_edi_enabled = fields.Boolean(
        string="ARCA Electronic Invoicing",
        help="Enable electronic invoicing via ARCA for this journal.",
        compute="_compute_l10n_ar_arca_edi_enabled",
        store=True,
        readonly=False,
    )

    @api.depends("l10n_ar_is_pos", "l10n_ar_afip_pos_system")
    def _compute_l10n_ar_arca_edi_enabled(self):
        for journal in self:
            journal.l10n_ar_arca_edi_enabled = (
                journal.l10n_ar_is_pos
                and journal.l10n_ar_afip_pos_system == "RLI_RLM"
            )
