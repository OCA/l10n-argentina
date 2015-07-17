# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2010 Pexego Sistemas Informáticos. All Rights Reserved
#    Copyright (C) 2010-2014 Eynes - Ingeniería del software All Rights Reserved
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import date, timedelta
import time

class account_bank_statement_line(osv.osv):
    
    def _check_amount(self, cr, uid, ids, context=None):
        return True
        
    _inherit = "account.bank.statement.line"
    _columns = {
        'payment_date': fields.date('Payment date'),
        'issue_date': fields.date('Issue date'),
        'aux_journal_id': fields.many2one('account.journal', 'Journal', select=True),
        'statement_id': fields.many2one('account.bank.statement', 'Statement', select=True, ondelete='restrict'),
    }

    def button_confirm_bank_statement_line(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'open'}, context=context)

    def button_draft_bank_statement_line(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'draft'}, context=context)

    def button_conciliated_bank_statement_line(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'open'}, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            st_lines = False
            journal_type = False
        else:           
            st_lines = context.get('st_lines',False)
            journal_type = context.get('journal_type',False)
            
        if st_lines and st_lines in 'remove':
            for id in ids:
                sql = 'delete from account_bank_statement_line where id = ' + str(id)
                cr.execute(sql)
            return super(account_bank_statement_line, self).unlink(cr, uid, ids, context)
        elif st_lines and st_lines in 'delete':
            for t in self.browse(cr, uid, ids, context=context):
                if t.state not in 'draft' or t.creation_type in 'system':
                    raise osv.except_osv(_('Invalid action !'), _('Cannot delete Account Bank Statement Line(s) which are not draft state o creation type is system !'))
                sql = 'delete from account_bank_statement_line where id = ' + str(t['id'])
                cr.execute(sql)
            return super(account_bank_statement_line, self).unlink(cr, uid, ids, context)
        else:
            if journal_type:
                if 'bank' in journal_type:
                    for t in self.browse(cr, uid, ids, context=context):
                        if t.state not in ('draft'):
                            raise osv.except_osv(_('Invalid action !'), _('Cannot remove Account Bank Statement Line(s) which are already confirm or conciliated!'))
                        else:
                             self.write(cr, uid, ids, {'statement_id': '', 'state': 'draft'})
                    return {}
                else:
                    t = self.browse(cr, uid, ids, context=context)
                    
                    if t:
                        if t.creation_type not in 'manual':
                            raise osv.except_osv(_('Invalid action !'), _('Cannot delete Account Bank Statement Line(s) which are not manual type!'))
                        sql = 'delete from account_bank_statement_line where id = ' + str(t['id'])
                        cr.execute(sql)
                    return super(account_bank_statement_line, self).unlink(cr, uid, ids, context)
            else:
                return super(account_bank_statement_line, self).unlink(cr, uid, ids, context)


class account_bank_statement(osv.osv):
    _inherit = "account.bank.statement"
    
    def button_confirm_bank(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for st in self.browse(cr, uid, ids, context=context):
            j_type = st.journal_id.type
            if not self.check_status_condition(cr, uid, st.state, journal_type=j_type):
                continue
            
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise osv.except_osv(_('Configuration Error!'), _('Please verify that an account is defined in the journal.'))
            for line in st.move_line_ids:
                if line.state != 'valid':
                    raise osv.except_osv(_('Error!'), _('The account entries lines are not in valid state.'))
            move_ids = []
            for st_line in st.line_ids:
                #~ escribo el movimiento como conciliado
                if st_line.state in 'draft':
                    self.pool.get('account.bank.statement.line').write(cr, uid, st_line.id, {'statement_id': ''})
                else:
                    self.pool.get('account.bank.statement.line').write(cr, uid, st_line.id, {'state': 'conciliated'})
                #~ compruebo los movimientos que son expense o income para generar los asientos
                if not st_line.type in ('expenses', 'income'):
                    continue
                #~ fin
                if not st_line.amount:
                    continue
                if st_line.account_id and not st_line.journal_entry_id.id:
                    #make an account move as before
                    vals = {
                        'debit': st_line.amount < 0 and -st_line.amount or 0.0,
                        'credit': st_line.amount > 0 and st_line.amount or 0.0,
                        'account_id': st_line.account_id.id,
                        'name': st_line.name,
                        #~ 'analytic_account_id': st_line.analytic_id and st_line.analytic_id.id
                    }
                    if st_line.analytic_id and st_line.type in 'expenses':
                        vals.update({'analytic_account_id': st_line.analytic_id.id})
                    self.pool.get('account.bank.statement.line').process_reconciliation(cr, uid, st_line.id, [vals], context=context)
                elif not st_line.journal_entry_id.id:
                    raise osv.except_osv(_('Error!'), _('All the account entries lines must be processed in order to close the statement.'))
                move_ids.append(st_line.journal_entry_id.id)
            if move_ids:
                self.pool.get('account.move').post(cr, uid, move_ids, context=context)
            self.message_post(cr, uid, [st.id], body=_('Statement %s confirmed, journal items were created.') % (st.name,), context=context)
            
            lines_to_statement = [(4, lid.id) for lid in st.line_ids]
            self.write(cr, uid, ids, {'line_ids':lines_to_statement})
            
            self.balance_check(cr, uid, st.id, journal_type=j_type, context=context)
                        
        self.link_bank_to_partner(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'state': 'confirm', 'closing_date': time.strftime("%Y-%m-%d %H:%M:%S")}, context=context)
            
account_bank_statement()

class account_check_deposit(osv.osv_memory):
    _inherit = 'account.check.deposit'
    
    def action_deposit(self, cr, uid, ids, context=None):
        third_check_obj = self.pool.get('account.third.check')
        
        aux = super(account_check_deposit, self).action_deposit(cr, uid, ids, context)
        record_ids = context.get('active_ids', [])
        
        check_objs = third_check_obj.browse(cr, uid, record_ids, context=context)

        for check in check_objs:
            
            if check.type in 'common':
                aux_payment_date = check.issue_date
            elif check.payment_date:
                aux_payment_date = check.payment_date
            else:
                aux_payment_date = check.deposit_date
                
            if check.clearing in '24':
                aux_payment_date = date(int(aux_payment_date[0:4]),int(aux_payment_date[5:7]),int(aux_payment_date[8:10])) + timedelta(days=1)
            elif check.clearing in '48':
                aux_payment_date = date(int(aux_payment_date[0:4]),int(aux_payment_date[5:7]),int(aux_payment_date[8:10])) + timedelta(days=2)
            elif check.clearing in '72':
                aux_payment_date = date(int(aux_payment_date[0:4]),int(aux_payment_date[5:7]),int(aux_payment_date[8:10])) + timedelta(days=3)

            st_line = {
                'name': 'Cheque de tercero ' + check.number,
                'issue_date': check.issue_date,
                'payment_date': aux_payment_date,
                'amount': check.amount,
                'account_id': check.deposit_bank_id.account_id.id,
                'state': 'draft',
                'type': 'receipt',
                'partner_id': check.source_partner_id.id,
                'creation_type': 'system',
                'ref_voucher_id': check.source_voucher_id.id,
                #~ 'ref': check.source_voucher_id.number,
                'ref': check.source_voucher_id.reference,
                'aux_journal_id': check.deposit_bank_id.journal_id.id,
            }

            st_id = self.pool.get('account.bank.statement.line').create(cr, uid, st_line, context)
            
        return True
        
account_check_deposit()

class account_check_reject(osv.osv_memory):
    _inherit = 'account.check.reject'
    
    def action_reject(self, cr, uid, ids, context=None):
        third_check_obj = self.pool.get('account.third.check')
        
        aux = super(account_check_reject, self).action_reject(cr, uid, ids, context)
        record_ids = context.get('active_ids', [])
        
        check_objs = third_check_obj.browse(cr, uid, record_ids, context=context)

        for check in check_objs:
            print check
            
            if check.type in 'common':
                aux_payment_date = check.issue_date
            elif check.payment_date:
                aux_payment_date = check.payment_date
            else:
                aux_payment_date = check.deposit_date
                
            if check.clearing in '24':
                aux_payment_date = date(int(aux_payment_date[0:4]),int(aux_payment_date[5:7]),int(aux_payment_date[8:10])) + timedelta(days=1)
            elif check.clearing in '48':
                aux_payment_date = date(int(aux_payment_date[0:4]),int(aux_payment_date[5:7]),int(aux_payment_date[8:10])) + timedelta(days=2)
            elif check.clearing in '72':
                aux_payment_date = date(int(aux_payment_date[0:4]),int(aux_payment_date[5:7]),int(aux_payment_date[8:10])) + timedelta(days=3)

            st_line = {
                'name': 'Cheque de tercero ' + check.number,
                'issue_date': check.issue_date,
                'payment_date': aux_payment_date,
                'amount': check.amount,
                'account_id': check.deposit_bank_id.account_id.id,
                'state': 'draft',
                'type': 'receipt',
                'partner_id': check.source_partner_id.id,
                'creation_type': 'system',
                'ref_voucher_id': check.source_voucher_id.id,
                #~ 'ref': check.source_voucher_id.number,
                'ref': check.source_voucher_id.reference,
                'aux_journal_id': check.deposit_bank_id.journal_id.id,
            }

            st_id = self.pool.get('account.bank.statement.line').create(cr, uid, st_line, context)
            
        return True
        
account_check_reject()
