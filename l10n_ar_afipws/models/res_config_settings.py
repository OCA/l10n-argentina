# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = "res.config.settings"

    afip_ws_env_type = fields.Selection(
        related="company_id.afip_ws_env_type", readonly=False
    )
