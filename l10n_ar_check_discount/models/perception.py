###############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (Gaston Bertolani)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PerceptionTaxLine(models.Model):
    _inherit = 'perception.tax.line'

    discount_id = fields.Many2one('check.discount', 'Check Discount', ondelete='cascade')

