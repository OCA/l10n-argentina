# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2008-2011  Thymbra
#    Copyright (c) 2011-2014 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#    All Rights Reserved. See AUTHORS for details.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, _
from odoo.exceptions import UserError, ValidationError
import time


class AccountCheckDeposit(models.Model):
    _name = 'account.check.deposit'

    def _get_journal(self, cr, uid, context=None):
        journal_id = False
        voucher_obj = self.env['account.payment.order']
        model = context.get('active_model', False)
        if model and model == 'account.third.check':
            ids = context.get('active_ids', [])
            vouchers = self.pool.get(model).read(cr, uid, ids, ['source_payment_order_id'], context=context)
            if vouchers and vouchers[0] and 'source_payment_order_id' in vouchers[0]:
                if vouchers[0]['source_payment_order_id']:
                    payment_order_id = vouchers[0]['source_payment_order_id'][0]
                    journal_id = voucher_obj.read(cr, uid, payment_order_id, ['journal_id'], context=context)['journal_id'][0]
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

    def view_init(self, cr, uid, fields_list, context=None):
        check_obj = self.pool.get('account.third.check')
        if context is None:
            context = {}
        for check in check_obj.browse(cr, uid, context.get('active_ids', []), context):
            if check.state != 'wallet':
                raise UserError(_("Error! The selected checks must be \
                    in wallet.\nCheck %s is not in wallet") % (check.number))
        pass

    # TODO: Esto deberiamos obtenerlo del anterior asiento contable. Tenemos
    # que guardar una referencia a los asientos contables de los cheques.
    # Por ahora, la cuenta contable de donde sacar el cheque la obtenemos de
    # la configuracion por compania
    def _get_source_account_check(self, cr, uid, company_id):
        check_config_obj = self.pool.get('account.check.config')

        # Obtenemos la configuracion
        res = check_config_obj.search(cr, uid, [('company_id', '=', company_id)])
        if not len(res):
            raise UserError(_('Error! There is no check \
                configuration for this Company!'))

        src_account = check_config_obj.read(cr, uid, res[0], ['account_id'])
        if 'account_id' in src_account:
            return src_account['account_id'][0]

        raise UserError(_('Error! Bad Treasury \
            configuration for this Company!'))

    def onchange_bank_account(self, cr, uid, ids, bank_account_id, context=None):

        bank_obj = self.pool.get('res.partner.bank')
        res = {'value': {}}

        if not bank_account_id:
            return res

        if not context:
            context = {}

        bank_acc = bank_obj.browse(cr, uid, bank_account_id, context)

        if bank_acc.journal_id:
            res['value']['journal_id'] = bank_acc.journal_id.id
        return res

    # TODO: Hacer un refactoring para poder depositar varios al mismo tiempo,
    # pero antes averiguar si se tiene que hacer un asiento por cada uno o
    # todo en un asiento por cuenta bancaria. Por ahora, esta hecho para
    # uno por asiento.
    def action_deposit(self, cr, uid, ids, context=None):
        third_check_obj = self.pool.get('account.third.check')

        move_line = self.pool.get('account.move.line')

        wizard = self.browse(cr, uid, ids[0], context=context)

        period_id = self.pool.get('account.period').find(cr, uid, wizard.date)[0]
        deposit_date = wizard.date or time.strftime('%Y-%m-%d')

        if not wizard.bank_account_id.account_id:
            raise UserError(_("Error! You have to configure an account on \
                Bank Account %s: %s") % (
                wizard.bank_account_id.bank_name,
                wizard.bank_account_id.acc_number))

        if context is None:
            context = {}
        record_ids = context.get('active_ids', [])
        company_id = wizard.company_id.id

        check_objs = third_check_obj.browse(cr, uid, record_ids, context=context)

        for check in check_objs:
            if check.state != 'wallet':
                raise UserError(_("Error! The selected checks must to be in \
                    cartera.\nCheck %s is not in wallet") % (check.number))

            if check.payment_date > deposit_date:
                raise UserError(_("Cannot deposit! You cannot deposit check %s \
                    because Payment Date is greater than \
                    Deposit Date.") % (check.number))

            account_check_id = self._get_source_account_check(cr, uid, company_id)

            # name = self.pool.get('ir.sequence').get_id(cr, uid,
            # check.payment_order_id.journal_id.id)

            if wizard.voucher_number:
                move_ref = _('Deposit Check %s [%s]') % (check.number, wizard.voucher_number)
            else:
                move_ref = _('Deposit Check %s') % (check.number)

            move_id = self.pool.get('account.move').create(cr, uid, {
                'name': '/',
                'journal_id': wizard.journal_id.id,
                'state': 'draft',
                'period_id': period_id,
                'date': deposit_date,
                #'to_check': True,
                'ref': move_ref,
            })

            move_line.create(cr, uid, {
                'name': _('Check Deposit'),
                #'centralisation': 'normal',
                'account_id': wizard.bank_account_id.account_id.id,
                'move_id': move_id,
                'journal_id': wizard.journal_id.id,
                'period_id': period_id,
                'date': deposit_date,
                'debit': check.amount,
                'credit': 0.0,
                'ref': _('Deposit Check %s on %s') % (check.number, wizard.bank_account_id.acc_number),
                'state': 'valid',
            })

            move_line.create(cr, uid, {
                'name': _('Check Deposit'),
                'centralisation': 'normal',
                'account_id': account_check_id,
                'move_id': move_id,
                'journal_id': wizard.journal_id.id,
                'period_id': period_id,
                'date': deposit_date,
                'debit': 0.0,
                'credit': check.amount,
                'ref': _('Deposit Check %s') % check.number,
                'state': 'valid',
            })

            check_vals = {'deposit_bank_id': wizard.bank_account_id.id, 'deposit_date': deposit_date, 'deposit_slip': wizard.voucher_number}
            check.write(check_vals)

            third_check_obj.deposit_check(cr, uid, [check.id], context=context)

            # Se postea el asiento llamando a la funcion post de account_move.
            # TODO: Se podria poner un check en el wizard para que elijan si postear
            # el asiento o no.
            self.pool.get('account.move').post(cr, uid, [move_id], context=context)

        return {'type': 'ir.actions.act_window_close'}
