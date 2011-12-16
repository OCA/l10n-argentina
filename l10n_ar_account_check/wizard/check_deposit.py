# coding=utf-8

#    Copyright (C) 2008-2011  Thymbra

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from osv import osv, fields
from tools.translate import _
import netsvc


class account_check_deposit(osv.osv_memory):
    _name = 'account.check.deposit'

    _columns = {
        'bank_account_id': fields.many2one('res.partner.bank', 'Bank Account',
            required=True),
        'date': fields.date('Deposit Date'),
    }

    def action_deposit(self, cr, uid, ids, context=None):
        third_check = self.pool.get('account.third.check')
        wf_service = netsvc.LocalService('workflow')

        move_line = self.pool.get('account.move.line')

        wizard = self.browse(cr, uid, ids[0], context=context)

        period_id = self.pool.get('account.period').find(cr, uid, wizard.date)[0]

        if context is None:
            context = {}
        record_ids = context.get('active_ids', [])

        check_objs = third_check.browse(cr, uid, record_ids, context=context)

        for check in check_objs:
            if check.state != 'C':
                raise osv.except_osv(
                    'Check %s is not in cartera?? !' % (check.number),
                    'The selected checks must to be in cartera.'
                )

            else:
                name = self.pool.get('ir.sequence').get_id(cr, uid,
                        check.voucher_id.journal_id.id)
                move_id = self.pool.get('account.move').create(cr, uid, {
                    'name': name,
                    'journal_id': check.voucher_id.journal_id.id,
                    'state': 'draft',
                    'period_id': period_id,
                    'date': wizard.date,
                    'ref': 'Check Deposit Nr. ' + check.number,
                })

                move_line.create(cr, uid, {
                    'name': name,
                    'centralisation': 'normal',
                    'account_id': wizard.bank_account_id.account_id.id,
                    'move_id': move_id,
                    'journal_id': check.voucher_id.journal_id.id,
                    'period_id': period_id,
                    'date': check.date,
                    'debit': check.amount,
                    'credit': 0.0,
                    'ref': 'Check Deposit Nro. ' + check.number,
                    'state': 'valid',
                })

                move_line.create(cr, uid, {
                    'name': name,
                    'centralisation': 'normal',
                    'account_id': check.voucher_id.journal_id.default_credit_account_id.id,
                    'move_id': move_id,
                    'journal_id': check.voucher_id.journal_id.id,
                    'period_id': period_id,
                    'date': check.date,
                    'debit': 0.0,
                    'credit': check.amount,
                    'ref': 'Check Deposit' + check.number,
                    'state': 'valid',
                })
                check.write({
                    'account_bank_id': wizard.bank_account_id.id
                })
                wf_service.trg_validate(uid, 'account.third.check', check.id,
                        'cartera_deposited', cr)

            self.pool.get('account.move').write(cr, uid, [move_id], {
                'state': 'posted',
            })

        return {}

account_check_deposit()
