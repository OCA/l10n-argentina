##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class DefaultJurisdictionConfiguration(models.Model):
    _name = 'report.default.jurisdiction.configuration'

    pos_ar_id = fields.Many2one(
        comodel_name='pos.ar',
        required=True,
        string="Point of Sale")
    state_id = fields.Many2one(
        comodel_name='res.country.state',
        required=True,
        string="State")

    @api.constrains('pos_ar_id', 'state_id')
    def _check_uniqueness(self):
        for rec in self:
            if rec.search_count([('pos_ar_id', '=', rec.pos_ar_id.id)]) > 1:
                raise ValidationError(_(
                    "You can not have more than one default for the " +
                    "same point of sale."))

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            name = '%s -> %s' % (rec.pos_ar_id.name, rec.state_id.name)
            res.append((rec.id, name))
        return res
