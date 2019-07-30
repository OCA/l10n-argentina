##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import api, models


class CheckDiscount(models.Model):
    _inherit = 'check.discount'

    @api.multi
    def _prepare_check_line_vals_for_move(self):
        res = super(CheckDiscount, self)._prepare_check_line_vals_for_move()
        other_checks = self.check_ids.filtered(
                lambda x: x.state != 'safekeeped')
        safekeeped_checks = self.check_ids.filtered(
            lambda c: c.state == 'safekeeped')
        if not other_checks:
            res = []
        if safekeeped_checks:
            wc_vals = {
                'account_id': self.check_config_id.safekept_account_id.id,
                'credit': sum(safekeeped_checks.mapped('amount')),
                'debit': 0.0,
                'currency_id': self.currency_id.id,
            }
            res.append(wc_vals)
        return res
