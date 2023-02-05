import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountMoveTax(models.Model):
    _name = "account.move.tax"
    _description = "account.move.tax"

    move_id = fields.Many2one("account.move", string="Account Move")
    tax_id = fields.Many2one("account.tax", string="Tax")
    base_amount = fields.Float("Base Amount")
    tax_amount = fields.Float("Tax Amount")
