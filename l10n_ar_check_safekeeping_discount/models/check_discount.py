###############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (Gaston Bertolani)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CheckDiscount(models.Model):
    _inherit = 'check.discount'

    @api.multi
    def _prepare_check_line_vals_for_move(self):
        other_checks = self.check_ids.filtered(
                lambda x: x.state != 'safekeeped')
        res = []
        if other_checks:
            res = super(CheckDiscount, self)._prepare_check_line_vals_for_move()
        safekeeped_checks = self.check_ids.filtered(
            lambda c: c.state == 'safekeeped')
        wc_vals = {
            'account_id': self.check_config_id.safekept_account_id.id,
            'credit': sum(safekeeped_checks.mapped('amount')),
            'debit': 0.0,
            'currency_id': self.currency_id.id,
        }
        res.append(wc_vals)
        return res
