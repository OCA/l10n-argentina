# -*- coding: utf-8 -*-
##############################################################################
#
#    Module for Odoo/OpenERP that adds Argentina's States (aka Provinces)
#    Copyright (C) Gabriel Davini. (<https://github.com/gabrielo77>).
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

import os

from openerp import _, api, exceptions, fields, models
from openerp.tools import convert_xml_import


class WizardInstallArgentineanCities(models.TransientModel):
    _name = 'wizard.install.argentinean.cities'
    _description = 'Install/Update Argentinean cities from an XML file'

    mode = fields.Selection(
        [
            ("update", "Update"),
            ("init", "Init"),
        ],
        string="Import Mode",
        default="update",
        required=True,
    )
    noupdate = fields.Boolean(string='No update?', default=False)

    def run(self, module, filename, mode, noupdate=False):
        return convert_xml_import(self.env.cr, module, filename, mode=mode, noupdate=noupdate)

    @api.multi
    def button_run(self):
        # get 'grandparent' (module) directory
        module_path = os.path.dirname(os.path.dirname(__file__))

        # get module name
        module_name = os.path.basename(module_path)

        # get XML data filename
        filename = os.path.join(module_path, "data/res_city_data.xml")
        if not os.path.exists(filename):
            raise exceptions.Warning(_("Can't import Cities because the XML is missing"))

        return self.run(module_name, filename, self.mode, self.noupdate)
