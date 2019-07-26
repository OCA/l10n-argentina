##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError
import time
from datetime import datetime


class AccountCheckDeposit(models.Model):
    _inherit = 'account.check.deposit'

    def view_init(self, fields_list):
        check_obj = self.env['account.third.check']
        record_ids = self.env.context.get('active_ids', [])
        for check in check_obj.browse(record_ids):
            if check.state not in ['wallet', 'safekeeped']:
                raise UserError(
                    _("Error! The selected checks must be in wallet " +
                      "or safekeeped.\nCheck %s is not in wallet or " +
                      "safekeeped") % (check.number))

    @api.multi
    def _prepare_move_line(self, check, account_id, move_id):
        deposit_date = self.date or time.strftime('%Y-%m-%d')
        line_vals = {
            'name': _('Check Deposit'),
            'account_id': account_id,
            'move_id': move_id,
            'journal_id': self.journal_id.id,
            'date': deposit_date,
            'debit': check.amount,
            'credit': 0.0,
            'ref': _('Deposit Check %s on %s') %
            (check.number, self.bank_account_id.acc_number),
        }
        return line_vals

    @api.multi
    def _prepare_counterpart_line(self, check, account_id, move_id):
        deposit_date = self.date or time.strftime('%Y-%m-%d')
        line_vals = {
            'name': _('Check Deposit'),
            'centralisation': 'normal',
            'account_id': account_id,
            'move_id': move_id,
            'journal_id': self.journal_id.id,
            'date': deposit_date,
            'debit': 0.0,
            'credit': check.amount,
            'ref': _('Deposit Check %s') % check.number,
        }
        return line_vals

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

    def action_deposit(self):
        period_obj = self.env['date.period']
        third_check_obj = self.env['account.third.check']
        move_line_obj = self.env['account.move.line']

        period_date = datetime.strptime(self.date, '%Y-%m-%d').date()
        period_id = period_obj._get_period(period_date).id
        deposit_date = self.date or time.strftime('%Y-%m-%d')
        if not self.bank_account_id.account_id:
            raise UserError(_("Error! You have to configure an account on \
                Bank Account %s: %s") % (
                self.bank_account_id.bank_name,
                self.bank_account_id.acc_number))

        record_ids = self.env.context.get('active_ids', [])
        company_id = self.company_id.id

        check_objs = third_check_obj.browse(record_ids)

        for check in check_objs:
            if check.state not in ['wallet', 'safekeeped']:
                raise UserError(
                    _("Error! The selected checks must to be in wallet or " +
                      "safekeeped.\nCheck %s is not in wallet or safekeeped")
                    % (check.number))

            if check.payment_date > deposit_date:
                raise UserError(
                    _("Cannot deposit! You cannot deposit check %s " +
                      "because Payment Date is greater than Deposit Date.")
                    % (check.number))

            account_check_id = self._get_source_account_check(company_id)

            if self.voucher_number:
                move_ref = _('Deposit Check %s [%s]') % (check.number,
                                                         self.voucher_number)
            else:
                move_ref = _('Deposit Check %s') % (check.number)

            move = self.env['account.move'].create({
                'name': '/',
                'journal_id': self.journal_id.id,
                'state': 'draft',
                'period_id': period_id,
                'date': deposit_date,
                'ref': move_ref,
            })
            ctx_validity = {'check_move_validity': False}
            account = self.bank_account_id.account_id
            line_vals = self._prepare_move_line(check, account.id, move.id)
            move_line_obj.with_context(ctx_validity).create(line_vals)

            if check.state == 'safekeeped':
                check_config = self.get_check_config()
                account_check_id = check_config.safekept_account_id.id

            line_vals = self._prepare_counterpart_line(
                check, account_check_id, move.id)
            move_line_obj.with_context(ctx_validity).create(line_vals)

            check_vals = {
                'deposit_bank_id': self.bank_account_id.id,
                'deposit_date': deposit_date,
                'deposit_slip': self.voucher_number
            }
            check.write(check_vals)
            check.deposit_check()
            move.post()

        return {'type': 'ir.actions.act_window_close'}
