##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime


class AccountCheckSafekeepingLot(models.Model):
    _name = 'account.check.safekeeping.lot'
    _description = 'check safekeeping'

    name = fields.Char(string="Name", default=_('New'))
    state = fields.Selection([
        ('new', _('New')),
        ('safekeeped', _('Safekeeped')),
        ('done', _('Done')),
        ], string='Status', readonly=True,
        copy=False, index=True,
        track_visibility='onchange', default='new',
        compute='_compute_state', store=True)
    check_ids = fields.One2many(
        'account.third.check',
        inverse_name='safekeeping_lot_id',
        string=_('Checks'))
    safekeep_date = fields.Date(string='Safekeep Date')
    journal_id = fields.Many2one('account.journal', 'Bank')
    note = fields.Text(string=_('Note'))

    @api.model
    def create(self, vals):
        seq = self.env['ir.sequence'].next_by_code(
            'seq.check.safekeeping') or '/-/'
        vals['name'] = seq
        return super().create(vals)

    @api.multi
    def unlink(self):
        for reg in self:
            bad_checks = reg.check_ids.filtered(
                    lambda x: x.state != 'wallet')
            if bad_checks:
                msg = (_(
                    "You cannot delete the lot %s because it " +
                    "has checks that are not in wallet") %
                    (reg.name))
                raise ValidationError(msg)
        res = super(AccountCheckSafekeepingLot, self).unlink()
        return res

    @api.depends(
        'check_ids', 'check_ids.state',
        'check_ids.safekeeping_move_id')
    def _compute_state(self):
        for lot in self:
            checks = lot.check_ids
            if checks.filtered(
                    lambda x: x.state == 'safekeeped'):
                lot.state = 'safekeeped'
            elif checks.filtered(
                    lambda x: x.state in ['deposited', 'delivered']):
                lot.state = 'done'
            else:
                lot.state = 'new'

    @api.model
    def get_check_config(self):
        check_config_obj = self.env['account.check.config']
        company = self.env.user.company_id
        configs = check_config_obj.search([
            ('company_id', '=', company.id)
        ])
        if not configs:
            raise ValidationError(
                    _("There is not check configuration for this company"))
        return configs[0]

    @api.multi
    def _prepare_move_line_vals(self, check):
        check_config = self.get_check_config()
        account = check_config.account_id
        if not account:
            raise ValidationError(_("Invalid Account"))
        line_vals = {
            'name': _('Safekeeped Check %s ') % (check.number),
            'account_id': account.id,
            'journal_id': self.journal_id.id,
            'date': self.safekeep_date,
            'credit': check.amount,
            'debit': 0.0,
        }
        return line_vals

    @api.multi
    def _prepare_counterpart_line(self, check):
        check_config = self.get_check_config()
        safekept_account = check_config.safekept_account_id
        if not safekept_account:
            raise ValidationError(_("Invalid Safekept Account"))
        # Counterpart vals
        counterpart_vals = {
            'name': _('Safekeeped Check %s ') % (check.number),
            'account_id': safekept_account.id,
            'journal_id': self.journal_id.id,
            'date': self.safekeep_date,
            'credit': 0.0,
            'debit': check.amount,
        }
        return counterpart_vals

    @api.multi
    def create_move(self, check):
        period_obj = self.env['date.period']
        move_obj = self.env['account.move']
        period_date = datetime.strptime(self.safekeep_date, '%Y-%m-%d')
        period_id = period_obj._get_period(period_date).id
        line_vals = self._prepare_move_line_vals(check)
        counterpart_vals = self._prepare_counterpart_line(check)
        all_line_lst = [line_vals] + [counterpart_vals]
        move_ref = _('Safekeeping Lot %s') % (self.name)
        move_vals = {
            'name': '/',
            'journal_id': self.journal_id.id,
            'state': 'draft',
            'period_id': period_id,
            'date': self.safekeep_date,
            'line_ids': [(0, False, mvl) for mvl in all_line_lst],
            # 'to_check': True,
            'ref': move_ref,
        }
        move = move_obj.create(move_vals)
        move.post()
        return move

    @api.multi
    def action_safekeep(self):
        if not self.check_ids:
            raise ValidationError(_("There is not third check related"))
        if not self.safekeep_date:
            self.safekeep_date = fields.Date.context_today(self)
        checks = self.check_ids.filtered(
            lambda x: x.state == 'wallet'or not x.safekeeping_move_id)
        for check in checks:
            move = self.create_move(check)
            check.write({'safekeeping_move_id': move.id})
        self.check_ids.action_safekeep()
        return True
