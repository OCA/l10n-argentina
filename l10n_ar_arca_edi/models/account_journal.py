# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ar_arca_edi_enabled = fields.Boolean(
        compute="_compute_l10n_ar_arca_edi_enabled",
        string="Issues electronic invoice (WSFEv1)",
        help="The journal issues electronic invoices through the ARCA WSFEv1 "
        "(domestic market). It requires the point of sale system to be "
        "'Online Invoice' (l10n_ar_afip_pos_system = RLI_RLM).",
    )

    @api.depends("l10n_ar_is_pos", "l10n_ar_afip_pos_system", "country_code")
    def _compute_l10n_ar_arca_edi_enabled(self):
        for journal in self:
            journal.l10n_ar_arca_edi_enabled = (
                journal.country_code == "AR"
                and journal.l10n_ar_is_pos
                and journal.l10n_ar_afip_pos_system == "RLI_RLM"
            )
