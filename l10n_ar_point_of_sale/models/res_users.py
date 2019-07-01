# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    property_default_pos_id = fields.Many2one('pos.ar', string=_('Default POS'),
        help=_('Select the Default Point of Sale'), company_dependent=True)
