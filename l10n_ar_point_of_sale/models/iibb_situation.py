##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import fields, models


class IIBBSituation(models.Model):
    _name = 'iibb.situation'

    name = fields.Char(string='Name', required=True)
