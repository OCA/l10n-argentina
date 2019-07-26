##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import _, api, models


class AccountThirdCheck(models.Model):
    _inherit = 'account.third.check'

    @api.multi
    def _validate_discountability(self):
        discounted_checks = self.env['account.third.check']
        wrong_state = self.env['account.third.check']
        wrong_type = self.env['account.third.check']
        for check in self:
            if check.discount_id:
                discounted_checks += check
            if check.state not in ['wallet', 'safekeeped']:
                wrong_state += check
            if check.type != 'postdated':
                wrong_type += check
        err = ""
        if discounted_checks:
            err += _("Some checks are already in a Discount:\n")
            err_lines = []
            for discounted_check in discounted_checks:
                err_lines.append(
                    _("Check '%s' [Amount: %s] in Discount '%s'") %
                    (discounted_check.number, discounted_check.amount,
                     discounted_check.discount_id.name))
            err += ("\n").join(err_lines) + "\n\n"
        if wrong_state:
            err += _("Some checks can't be Discounted because of the state:\n")
            err_lines = []
            for ws_check in wrong_state:
                err_lines.append(
                    _("Check '%s' [Amount: %s] with State '%s'") %
                    (ws_check.number, ws_check.amount, ws_check.state))
            err += ("\n").join(err_lines) + "\n\n"
        if wrong_type:
            err += _("Some checks can't be Discounted because of " +
                     "their Type:\n")
            err_lines = []
            for wt_check in wrong_type:
                err_lines.append(
                    _("Check '%s' [Amount: %s] with Type '%s'") %
                    (wt_check.number, wt_check.amount, wt_check.type))
            err += ("\n").join(err_lines) + "\n\n"
        return err
