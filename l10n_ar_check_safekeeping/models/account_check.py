##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import _, models, api, fields
from odoo.exceptions import ValidationError


class AccountThirdCheck(models.Model):
    _name = 'account.third.check'
    _inherit = 'account.third.check'

    state = fields.Selection(
        selection_add=[('safekeeped', _('Safekeeped'))])
    safekeep_date = fields.Date(
        string='Safekeep Date')
    safekeeping_lot_id = fields.Many2one(
        'account.check.safekeeping.lot',
        string=_('Safekeeping Lot'))
    safekeeping_move_id = fields.Many2one('account.move', 'Safekeeping Move')

    @api.multi
    def action_safekeep(self):
        for check in self:
            check.state = 'safekeeped'
            check.safekeep_date = fields.Date.context_today(self)

    @api.multi
    def move_to_wallet(self):
        wrong_state = self.env['account.third.check']
        for check in self:
            if check.state != 'safekeeped':
                wrong_state += check
        if wrong_state:
            err = _("Some checks can't be Safekeeped because of the state:\n")
            err_lines = []
            for ws_check in wrong_state:
                err_lines.append(
                    _("Check '%s' [Amount: %s] with State '%s'") %
                    (ws_check.number, ws_check.amount, ws_check.state))
            err += ("\n").join(err_lines) + "\n\n"
            raise ValidationError(err)
        for check in self:
            move = check.safekeeping_move_id
            move.button_cancel()
            move.unlink()
            check.safekeeping_lot_id = False
            check.state = 'wallet'
