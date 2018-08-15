###############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (Cardozo Nicolás Joaquin)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging
from datetime import date, datetime
from odoo import models, fields, api


_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    @api.depends('date_invoice')
    def _compute_period(self):
        for rec in self:
            if rec.date_invoice:
                period_obj = rec.env['date.period']
                period_date = datetime.strptime(rec.date_invoice, '%Y-%m-%d').date()
                period = period_obj._get_period(period_date)
                rec.period_id = period.id

    period_id = fields.Many2one(string="Period", comodel_name="date.period",
                                compute='_compute_period', store=True)