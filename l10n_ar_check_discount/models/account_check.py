##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountThirdCheck(models.Model):
    _name = 'account.third.check'
    _inherit = 'account.third.check'

    state = fields.Selection(
        selection_add=[('discounted', _('Discounted'))])
    discount_ids = fields.Many2many(
        comodel_name='check.discount',
        relation='third_check_discount_rel',
        column2='check_discount_id', column1='account_third_check_id',
        string="Discount Document")
    discount_id = fields.Many2one(
        comodel_name='check.discount',
        compute="_compute_discount_id", store=True,
        string="Discount Document")
    discount_date = fields.Date(
        string='Discount Date')

    @api.depends('discount_ids')
    def _compute_discount_id(self):
        for check in self:
            check.discount_id = check.discount_ids and check.discount_ids[0]

    @api.multi
    def discount_checks(self):
        validation = self._validate_discountability()
        if validation:
            raise ValidationError(validation)

        discount_model = self.env['check.discount']
        create_vals = self._prepare_check_discount_vals()
        discount = discount_model.create(create_vals)
        action = self._prepare_discount_action(discount)
        return action

    @api.multi
    def _prepare_discount_action(self, discount):
        action = {
            'name': _('Current Inventory'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'check.discount',
            'type': 'ir.actions.act_window',
            'res_id': discount.id,
            'target': 'current',
        }
        return action

    @api.multi
    def _prepare_check_discount_vals(self):
        vals = {
            'check_ids': [(6, 0, self.ids)],
        }
        return vals

    @api.multi
    def _validate_discountability(self):
        discounted_checks = self.env['account.third.check']
        wrong_state = self.env['account.third.check']
        wrong_type = self.env['account.third.check']
        for check in self:
            if check.discount_id:
                discounted_checks += check
            if check.state != 'wallet':
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


class AccountCheckConfig(models.Model):
    _inherit = 'account.check.config'

    discount_invoice_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Check Discount Invoice Journal')

    discount_move_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Check Discount Move Journal')

    discount_payment_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Check Discount Payment Journal')
