##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import fields, models


class SifereJurisdiction(models.Model):
    _name = 'sifere.jurisdiction'

    state = fields.Many2one('res.country.state', required=True)
    code = fields.Integer('Code', required=True)
    config_id = fields.Many2one('sifere.config')


class SifereConfig(models.Model):
    _name = 'sifere.config'
    _rec_name = 'name'

    name = fields.Char('Name', required=True)
    jurisdiction_ids = fields.One2many(
        'sifere.jurisdiction', 'config_id', string='Jurisdictions')
    ignore_jurisdiction = fields.Boolean(
        'Ignore jurisdiction errors?', default=False)
