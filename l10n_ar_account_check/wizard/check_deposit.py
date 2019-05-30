###############################################################################
#   Copyright (C) 2008-2011  Thymbra
#   Copyright (c) 2012-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from odoo import api, models, fields, _
from odoo.exceptions import UserError
import time
from datetime import datetime


class AccountCheckDeposit(models.Model):
    _name = 'account.check.deposit'

    @api.model
    def _get_journal(self):
        journal_id = False
        voucher_obj = self.env['account.payment.order']
        model = self.env.context.get('active_model', False)
        if model and model == 'account.third.check':
            ids = self.env.context.get('active_ids', [])
            vouchers = self.env[model].browse(ids).read(
                ['source_payment_order_id'])
            if vouchers and vouchers[0] and \
                    'source_payment_order_id' in vouchers[0]:
                if vouchers[0]['source_payment_order_id']:
                    payment_order_id = vouchers[0][
                        'source_payment_order_id'][0]
                    journal_id = voucher_obj.browse(payment_order_id).read(
                        ['journal_id'])[0]['journal_id'][0]
        return journal_id

    journal_id = fields.Many2one(comodel_name='account.journal',
                                 string='Journal',
                                 required=True,
                                 domain=[('type', 'in', ('cash', 'bank'))],
                                 default=_get_journal)
    bank_account_id = fields.Many2one(comodel_name='res.partner.bank',
                                      string='Bank Account', required=True)
    date = fields.Date(string='Deposit Date', required=True,
                       default=lambda *a: time.strftime('%Y-%m-%d'))
    voucher_number = fields.Char(string='Voucher Number', size=32)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.user.company_id.id)

    def view_init(self, fields_list):
        check_obj = self.env['account.third.check']
        record_ids = self.env.context.get('active_ids', [])
        for check in check_obj.browse(record_ids):
            if check.state != 'wallet':
                raise UserError(_("Error! The selected checks must be \
                    in wallet.\nCheck %s is not in wallet") % (check.number))
        pass

    # TODO: Esto deberiamos obtenerlo del anterior asiento contable. Tenemos
    # que guardar una referencia a los asientos contables de los cheques.
    # Por ahora, la cuenta contable de donde sacar el cheque la obtenemos de
    # la configuracion por compania
    def _get_source_account_check(self, company_id):
        check_config_obj = self.env['account.check.config']

        # Obtenemos la configuracion
        res = check_config_obj.search([('company_id', '=', company_id)])
        if not len(res):
            raise UserError(_('Error! There is no check \
                configuration for this Company!'))
        src_account = res.read(['account_id'])[0]
        if 'account_id' in src_account:
            return src_account['account_id'][0]

        raise UserError(_('Error! Bad Treasury \
            configuration for this Company!'))

    @api.onchange('bank_account_id')
    def onchange_bank_account(self):
        if not self.bank_account_id:
            return

        bank_acc = self.bank_account_id
        if bank_acc.journal_id:
            self.journal_id = bank_acc.journal_id.id

    # TODO: Hacer un refactoring para poder depositar varios al mismo tiempo,
    # pero antes averiguar si se tiene que hacer un asiento por cada uno o
    # todo en un asiento por cuenta bancaria. Por ahora, esta hecho para
    # uno por asiento.
    # TODO: action_deposit create a unbalanced journal entr now, the
    # journal entryes be created with context 'check_move_validity': False
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
            if check.state != 'wallet':
                raise UserError(_("Error! The selected checks must to be in \
                    cartera.\nCheck %s is not in wallet") % (check.number))

            if check.payment_date > deposit_date:
                raise UserError(_("Cannot deposit! You cannot deposit check %s \
                    because Payment Date is greater than \
                    Deposit Date.") % (check.number))

            account_check_id = self._get_source_account_check(company_id)

            # name = self.pool.get('ir.sequence').get_id(cr, uid,
            # check.payment_order_id.journal_id.id)

            if self.voucher_number:
                move_ref = _('Deposit Check %s [%s]') % (check.number,
                                                         self.voucher_number)
            else:
                move_ref = _('Deposit Check %s') % (check.number)

            move_id = self.env['account.move'].create({
                'name': '/',
                'journal_id': self.journal_id.id,
                'state': 'draft',
                'period_id': period_id,
                'date': deposit_date,
                # 'to_check': True,
                'ref': move_ref,
            })
            move_line_obj.with_context({'check_move_validity': False}).create({
                'name': _('Check Deposit'),
                # 'centralisation': 'normal',
                'account_id': self.bank_account_id.account_id.id,
                'move_id': move_id.id,
                'journal_id': self.journal_id.id,
                'period_id': period_id,
                'date': deposit_date,
                'debit': check.amount,
                'credit': 0.0,
                'ref': _('Deposit Check %s on %s') %
                (check.number, self.bank_account_id.acc_number),
            })

            move_line_obj.with_context({'check_move_validity': False}).create({
                'name': _('Check Deposit'),
                'centralisation': 'normal',
                'account_id': account_check_id,
                'move_id': move_id.id,
                'journal_id': self.journal_id.id,
                'period_id': period_id,
                'date': deposit_date,
                'debit': 0.0,
                'credit': check.amount,
                'ref': _('Deposit Check %s') % check.number,
            })

            check_vals = {
                'deposit_bank_id': self.bank_account_id.id,
                'deposit_date': deposit_date,
                'deposit_slip': self.voucher_number,
                'deposit_move_id': move_id.id,
            }
            check.write(check_vals)

            check.deposit_check()

            # Se postea el asiento llamando a la funcion post de account_move.
            # TODO: Se podria poner un check en el wizard
            # para que elijan si postear el asiento o no.
            move_id.post()

        return {'type': 'ir.actions.act_window_close'}
