##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import fields, models


class AccountCheckConfig(models.Model):
    _inherit = 'account.check.config'

    safekept_account_id = fields.Many2one(
        'account.account', 'Safekept Check Account',
        required=True, help="Account for checks in safekeeping")
