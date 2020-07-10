# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2015 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2015 Eynes (http://www.eynes.com.ar)
#    Copyright (c) 2015 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#    All Rights Reserved. See AUTHORS for details.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import re

from openerp import api, fields, models


class ResCountry(models.Model):
    _inherit = 'res.country'

    wsfex_country_code_ids = fields.One2many(
        'wsfex.dst_country.codes',
        'country_id',
        string='WSFEX Country Codes',
        help="The codes assgined by AFIP to this Country for export and import operations.",
    )
    afip_code = fields.Char(string='AFIP Code', size=3, compute="_calc_afip_code",
                            inverse="_set_afip_code")

    @api.depends("wsfex_country_code_ids")
    def _calc_afip_code(self):
        for country in self:
            afip_code = ""
            if country.wsfex_country_code_ids:
                afip_code = country.wsfex_country_code_ids.sorted(lambda c: c.code)[0].code

            country.afip_code = afip_code

    def _set_afip_code(self):
        for country in self:
            country.wsfex_country_code_ids.write({"afip_code": country.afip_code})

    def get_or_create_country_for_wsfex(self, name, do_create=True):
        # Remove irrelevanta data between parenthesis in the given name
        match = re.match(r"(^.+)\s(\(.*\))", name)
        if match:
            name_to_search = match.groups()[0]
        else:
            name_to_search = name

        # 'Reino' comes abbreviated as 'R.'
        #if 'R.' in name_to_search:
        #    name_to_search = name_to_search.replace('R.', 'Reino')

        # 'San' and 'Santa' comes abbreviated as 'S.'
        #if 'S.' in name_to_search:
        #    if name_to_search[-1].lower() == "a":
        #        name_to_search = name_to_search.replace('S.', 'Santa')
        #    else:
        #        name_to_search = name_to_search.replace('S.', 'San')

        country = self.search([("name", "ilike", name_to_search)])
        if len(country) > 1:
            country = self.search([("name", "=ilike", name_to_search)])

        if not country and do_create:
            country = self.create({"name": name})

        return country
