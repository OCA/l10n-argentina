##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.onchange("city_id")
    def onchange_city_id(self):
        self.city = self.city_id.name

    city_id = fields.Many2one('res.city', string='City')
    zip = fields.Char(related="city_id.zip_code", store=True, readonly=False)
    state_id = fields.Many2one(related="city_id.state_id",
                               store=True, readonly=False)
    country_id = fields.Many2one(related="city_id.state_id.country_id",
                                 store=True, readonly=False)


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.onchange("city_id")
    def onchange_city_id(self):
        self.city = self.city_id.name

    city_id = fields.Many2one('res.city', string='City')
    zip = fields.Char(related="city_id.zip_code", store=True, readonly=False)
    state_id = fields.Many2one(related="city_id.state_id",
                               store=True, readonly=False)
    country_id = fields.Many2one(related="city_id.state_id.country_id",
                                 store=True, readonly=False)
