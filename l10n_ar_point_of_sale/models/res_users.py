##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import fields, models, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    property_default_pos_id = fields.Many2one(
        'pos.ar', string=_('Default POS'),
        help=_('Select the Default Point of Sale'), company_dependent=True)
