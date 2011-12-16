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


class account_check_reject(osv.osv_memory):
    _name = 'account.check.reject'

    _columns = {
        'reject_date': fields.date('Deposit Date', required=True),
        'expense_account': fields.many2one('account.account',
            'Expense Account'),
        'expense_amount': fields.float('Expense Amount'),
        'invoice_expense': fields.boolean('Invoice Expense?'),
        'no_expense': fields.boolean('No Expenses ?'),
    }

    def _get_address_invoice(self, cr, uid, partner):
        partner_obj = self.pool.get('res.partner')
        return partner_obj.address_get(cr, uid, [partner],
                ['contact', 'invoice'])

    def action_reject(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        record_ids = context.get('active_ids', [])
        third_check = self.pool.get('account.third.check')
        check_objs = third_check.browse(cr, uid, record_ids, context=context)

        third_check = self.pool.get('account.third.check')
        wf_service = netsvc.LocalService('workflow')
        invoice_obj = self.pool.get('account.invoice')
        move_line = self.pool.get('account.move.line')
        invoice_line_obj = self.pool.get('account.invoice.line')
        wizard = self.browse(cr, uid, ids[0], context=context)

        period_id = self.pool.get('account.period').find(cr, uid,
                wizard.reject_date)[0]

        for check in check_objs:
            if check.state != 'C':
                raise osv.except_osv(
                    'Check %s is not in cartera?? !' % (check.number),
                    'The selected checks must to be in cartera.'
                )
            partner_address = self._get_address_invoice(cr, uid,
                    check.voucher_id.partner_id.id)
            contact_address = partner_address['contact']
            invoice_address = partner_address['invoice']
            invoice_vals = {
                'name': check.number,
                'origin': 'Rejected Check' + (check.number or '') + ',' + (check.voucher_id.number),
                'type': 'out_debit',
                'account_id': check.voucher_id.partner_id.property_account_receivable.id,
                'partner_id': check.voucher_id.partner_id.id,
                'address_invoice_id': invoice_address,
                'address_contact_id': contact_address,
                'date_invoice': wizard.reject_date,
            }

            invoice_id = invoice_obj.create(cr, uid, invoice_vals)

            invoice_line_vals = {
                'name': 'Check Rejected' + check.number,
                'origin': 'Check Rejected' + check.number,
                'invoice_id': invoice_id,
                'account_id': check.voucher_id.journal_id.default_credit_account_id.id,
                'price_unit': check.amount,
                'quantity': 1,
            }
            invoice_line_obj.create(cr, uid, invoice_line_vals)
            check.write({'reject_debit_note': invoice_id})

            if not wizard.no_expense:
                if wizard.invoice_expense:
                    if  wizard.expense_amount != 0.00 \
                    and wizard.expense_account:
                        invoice_line_obj.create(cr, uid, {
                            'name': 'Check Rejected Expenses' + check.number,
                            'origin': 'Check Rejected' + check.number,
                            'invoice_id': invoice_id,
                            'account_id': wizard.expense_account.id,
                            'price_unit': wizard.expense_amount,
                            'quantity': 1,
                        })
                    else:
                        raise osv.except_osv(_('Error'),
                            _('You Must Assign expense account and amount !'))

                else:
                    if  wizard.expense_amount != 0.00 \
                    and wizard.expense_account:
                        name = self.pool.get('ir.sequence').get_id(cr, uid,
                                check.voucher_id.journal_id.id)
                        move_id = self.pool.get('account.move').create(cr, uid, {
                            'name': name,
                            'journal_id': check.voucher_id.journal_id.id,
                            'state': 'draft',
                            'period_id': period_id,
                            'date': wizard.reject_date,
                            'ref': 'Rejected Check ' + check.number,
                        })

                        move_line.create(cr, uid, {
                            'name': name,
                            'centralisation': 'normal',
                            'account_id': wizard.expense_account.id,
                            'move_id': move_id,
                            'journal_id': check.voucher_id.journal_id.id,
                            'period_id': period_id,
                            'date': wizard.reject_date,
                            'debit': wizard.expense_amount,
                            'credit': 0.0,
                            'ref': 'Check Reject Nro. ' + check.number,
                            'state': 'valid',
                        })

                        move_line.create(cr, uid, {
                            'name': name,
                            'centralisation': 'normal',
                            'account_id': check.voucher_id.journal_id.default_credit_account_id.id,
                            'move_id': move_id,
                            'journal_id': check.voucher_id.journal_id.id,
                            'period_id': period_id,
                            'date': wizard.reject_date,
                            'debit': 0.0,
                            'credit': wizard.expense_amount,
                            'ref': 'Check Reject' + check.number,
                            'state': 'valid',
                        })
                        self.pool.get('account.move').write(cr, uid, [move_id], {
                            'state': 'posted',
                        })

            wf_service.trg_validate(uid, 'account.third.check', check.id,
                    'cartera_rejected', cr)

        return {}

account_check_reject()
