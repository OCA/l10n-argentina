# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014-TODAY Eynes (<http://www.e-mips.com.ar>)
#
#    This is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    city_id = fields.Many2one('res.city', string='City')
    zip = fields.Char(related="city_id.zip_code", store=True, readonly=False)
    state_id = fields.Many2one(related="city_id.state_id", store=True, readonly=False)
    country_id = fields.Many2one(related="city_id.state_id.country_id", store=True, readonly=False)


class ResCompany(models.Model):
    _inherit = "res.company"

    city_id = fields.Many2one('res.city', string='City')
    zip = fields.Char(related="city_id.zip_code", store=True, readonly=False)
    state_id = fields.Many2one(related="city_id.state_id", store=True, readonly=False)
    country_id = fields.Many2one(related="city_id.state_id.country_id", store=True, readonly=False)
