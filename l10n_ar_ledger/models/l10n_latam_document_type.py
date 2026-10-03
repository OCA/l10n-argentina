##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class L10nLatamDocumentType(models.Model):
    _inherit = "l10n_latam.document.type"

    export_to_digital = fields.Boolean(
        "Export to Digital",
        help="Set this to export this document on Digital VAT Ledger",
    )
