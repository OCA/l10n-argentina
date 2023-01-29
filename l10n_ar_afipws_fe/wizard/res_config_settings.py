from odoo import fields, models

# from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    afip_auth_verify_type = fields.Selection(
        related="company_id.afip_auth_verify_type",
        readonly=False,
    )
