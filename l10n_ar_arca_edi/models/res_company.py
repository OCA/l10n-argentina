# Copyright 2026 Leonobitech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ar_arca_certificate_id = fields.Many2one(
        "l10n_ar.arca.certificate",
        string="ARCA Certificate",
        domain="[('company_id', '=', id), ('state', '=', 'active')]",
        help="Active ARCA digital certificate for electronic invoicing.",
    )
