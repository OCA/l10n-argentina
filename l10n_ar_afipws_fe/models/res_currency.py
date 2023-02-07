# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files


import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    _inherit = "res.currency"
