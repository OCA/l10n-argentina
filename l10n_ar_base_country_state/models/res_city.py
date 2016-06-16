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

from openerp import models, fields, api


class ResCity(models.Model):
    _name = 'res.city'
    _description = 'Cities'

    @api.onchange("state_id")
    def onchange_state_id(self):
        if self.state_id and self.country_id != self.state_id.country_id:
            self.country_id = self.state_id.country_id and self.state_id.country_id.id

    def default_country_id(self):
        return self.env.ref("base.ar").id

    name = fields.Char(string='City', size=64, required=True)
    zip_code = fields.Char(string='Zip', size=24)
    afip_code = fields.Char(string='AFIP Code', size=16)
    country_id = fields.Many2one('res.country', string='Country', default=default_country_id)
    state_id = fields.Many2one('res.country.state', string='Country State')
