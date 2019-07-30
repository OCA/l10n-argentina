##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import fields, models


class PerceptionTaxLine(models.Model):
    _inherit = 'perception.tax.line'

    discount_id = fields.Many2one(
        'check.discount', 'Check Discount', ondelete='cascade')
