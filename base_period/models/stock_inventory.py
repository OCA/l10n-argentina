##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from datetime import datetime

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DSDTF


class StockInventory(models.Model):
    _name = 'stock.inventory'
    _inherit = 'stock.inventory'

    @api.depends('date')
    def _compute_period(self):
        for rec in self:
            if not rec.date:
                continue
            period_obj = rec.env['date.period']
            period_date = datetime.strptime(
                rec.date, DSDTF).date()
            period = period_obj._get_period(period_date)
            rec.period_id = period.id

    period_id = fields.Many2one(
        string="Period", comodel_name="date.period",
        compute='_compute_period', store=True)
