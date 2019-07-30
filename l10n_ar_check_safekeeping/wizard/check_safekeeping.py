##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CheckSafekeepingWizard(models.Model):
    _name = 'check.safekeeping.wizard'

    safekeeping_lot_id = fields.Many2one(
        'account.check.safekeeping.lot', 'Safekeeping Lot')

    @api.multi
    def action_done(self):
        check_obj = self.env['account.third.check']
        safekeeping_lot_obj = self.env['account.check.safekeeping.lot']
        ctx = self.env.context
        active_ids = ctx.get('active_ids', [])
        checks = check_obj.browse(active_ids)
        wrong_checks = checks.filtered(
                lambda x: x.state != 'wallet')
        if wrong_checks:
            checks_name = ', '.join(wrong_checks.mapped('number'))
            msg = _("Error! The selected checks must be \
                    in wallet.\nChecks %s is not in wallet") % (checks_name)
            raise ValidationError(msg)
        lot_reg = self.safekeeping_lot_id
        if lot_reg:
            checks.write({'safekeeping_lot_id': lot_reg.id})
            if lot_reg.state == 'safekeeped':
                lot_reg.action_safekeep()
        else:
            lot_reg = safekeeping_lot_obj.create({'state': 'new'})
            checks.write({'safekeeping_lot_id': lot_reg.id})
        form = self.env.ref(
            'l10n_ar_check_safekeeping.account_check_safekeeping_lot_form')
        act_window = {
            'name': _('Safekeeping Lot'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.check.safekeeping.lot',
            'res_id': lot_reg.id,
            'views': [(form.id, 'form')],
            'view_id': form.id,
            'target': 'current',
        }
        return act_window
