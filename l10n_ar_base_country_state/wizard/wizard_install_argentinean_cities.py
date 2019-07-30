##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
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
        return convert_xml_import(
            self.env.cr, module,
            filename, mode=mode,
            noupdate=noupdate)

    @api.multi
    def button_run(self):
        # get 'grandparent' (module) directory
        module_path = os.path.dirname(os.path.dirname(__file__))

        # get module name
        module_name = os.path.basename(module_path)

        # get XML data filename
        filename = os.path.join(module_path, "data/res_city_data.xml")
        if not os.path.exists(filename):
            raise exceptions.Warning(
                _("Can't import Cities because the XML is missing"))

        return self.run(module_name, filename, self.mode, self.noupdate)
