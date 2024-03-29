# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    afip_auth_verify_type = fields.Selection(
        [
            ("not_available", "Not Available"),
            ("available", "Available"),
            ("required", "Required"),
        ],
        default="not_available",
        string="AFIP authorization verification",
        help="It adds an option on invoices to verify the afip authorization "
        "data (for documents with CAE, CAI or CAEA).\n"
        "If you choose required, then on supplier invoices, verification is "
        "mandatory before invoice validation",
    )
