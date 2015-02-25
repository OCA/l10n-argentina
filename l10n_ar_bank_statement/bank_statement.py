# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2010 Pexego Sistemas Informáticos. All Rights Reserved
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

from osv import osv, fields
from tools.translate import _

class account_bank_statement_line(osv.osv):
    
    def _check_amount(self, cr, uid, ids, context=None):
        return True
        
    _name = "account.bank.statement.line"
    _inherit = "account.bank.statement.line"
    _columns = {
        'creation_type': fields.char('Creation type', size=50, help="System: created by OpenERP, Manual: created by the user"),
        'payment_date': fields.date('Payment date'),
        'issue_date': fields.date('Issue date'),
        'date': fields.date('Date'),
        'journal_id': fields.many2one('account.journal', 'Journal', select=True),
    }
    
    def bank_line_on_change_amount(self, cr, uid, ids, type, amount, context=None):
        print 'signos'
        """
        Force withdrawal movements to be negative and deposit ones to
        be positive.
        """
        if type == 'expense':
            amount = -abs(amount)
        elif type == 'income':
            amount = abs(amount)

        return { 'value': { 'amount': amount } }

    def button_confirm_bank_statement_line(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'open'}, context=context)

    def button_draft_bank_statement_line(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'draft'}, context=context)

    def button_conciliated_bank_statement_line(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'open'}, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        print context
        if context is None:
            st_lines = False
            journal_type = ''
        else:           
            st_lines = context.get('st_lines',False)
            journal_type = context.get('journal_type',False)
            
        if st_lines:
            for t in self.browse(cr, uid, ids, context=context):
                if t.state not in 'draft' or t.creation_type in 'system':
                    raise osv.except_osv(_('Invalid action !'), _('Cannot delete Account Bank Statement Line(s) which are not draft state o creation type is system !'))
                sql = 'delete from account_bank_statement_line where id = ' + str(t['id'])
                cr.execute(sql)
            return {}
        else:
            if journal_type:
                if 'bank' in journal_type:
                    for t in self.browse(cr, uid, ids, context=context):
                        if t.state not in ('draft'):
                            raise osv.except_osv(_('Invalid action !'), _('Cannot remove Account Bank Statement Line(s) which are already confirm !'))
                        else:
                             self.write(cr, uid, ids, {'statement_id': '', 'state': 'draft'})
                    return {}
                else:
                    t = self.browse(cr, uid, ids, context=context)

                    if t.state not in ('draft'):
                        raise osv.except_osv(_('Invalid action !'), _('Cannot delete Account Bank Statement Line(s) which are not draft state !'))
                    sql = 'delete from account_bank_statement_line where id = ' + str(t['id'])
                    cr.execute(sql)
                    return {}
            else:
                print 'tt'
                print ids
                sql = 'delete from account_bank_statement_line where id = ' + str(ids)
                cr.execute(sql)
                return {}

account_bank_statement_line()

class account_bank_statement(osv.osv):
    
    _name = "account.bank.statement"
    _inherit = "account.bank.statement"

    def _get_statement(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.bank.statement.line').browse(cr, uid, ids, context=context):
            result[line.statement_id.id] = True
        return result.keys()
    
    def _end_balance(self, cursor, user, ids, name, attr, context=None):
        res = {}
        for statement in self.browse(cursor, user, ids, context=context):
            res[statement.id] = statement.balance_start
            for line in statement.line_ids:
                res[statement.id] += line.amount
        return res
    
    def _diference(self, cursor, user, ids, name, attr, context=None):
        res = {}
        for statement in self.browse(cursor, user, ids, context=context):
            res[statement.id] = statement.balance_end_real - statement.balance_end
        return res
    
    def balance_check(self, cr, uid, st_id, journal_type='bank', context=None):
        st = self.browse(cr, uid, st_id, context=context)
        if not ((abs((st.balance_end or 0.0) - st.balance_end_real) < 0.0001) or (abs((st.balance_end or 0.0) - st.balance_end_real) < 0.0001)):
            raise osv.except_osv(_('Error!'),
                    _('The statement balance is incorrect !\nThe expected balance (%.2f) is different than the computed one. (%.2f)') % (st.balance_end_real, st.balance_end))
        return True
        
    _columns = {
        'balance_end': fields.function(_end_balance,
            store = {
                'account.bank.statement': (lambda self, cr, uid, ids, c={}: ids, ['line_ids','move_line_ids','balance_start'], 10),
                'account.bank.statement.line': (_get_statement, ['amount'], 10),
            },
            string="Computed Balance", help='Balance as calculated based on Starting Balance and transaction lines'),
        'diference': fields.function(_diference, string="Diference", type="float", help="Diference between calculated and balance end")
    }
            
    def button_confirm_bank(self, cr, uid, ids, context=None):
        print 'sequence'
        print 'banco'
        obj_seq = self.pool.get('ir.sequence')
        if context is None:
            context = {}

        for st in self.browse(cr, uid, ids, context=context):
            j_type = st.journal_id.type
            company_currency_id = st.journal_id.company_id.currency_id.id
            if not self.check_status_condition(cr, uid, st.state, journal_type=j_type):
                continue
            
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise osv.except_osv(_('Configuration Error !'),
                        _('Please verify that an account is defined in the journal.'))

            if not st.name == '/':
                st_number = st.name
            else:
                c = {'fiscalyear_id': st.period_id.fiscalyear_id.id}
                if st.journal_id.sequence_id:
                    st_number = obj_seq.next_by_id(cr, uid, st.journal_id.sequence_id.id, context=c)
                else:
                    st_number = obj_seq.next_by_code(cr, uid, 'account.bank.statement', context=c)

            for line in st.move_line_ids:
                if line.state <> 'valid':
                    raise osv.except_osv(_('Error !'),
                            _('The account entries lines are not in valid state.'))
                            
            aux_conciliated = 0
            for st_line in st.line_ids:
                if st_line.state in 'draft':
                    self.pool.get('account.bank.statement.line').write(cr, uid, st_line.id, {'statement_id': ''})
                #~ elif st_line.state in ('open','conciliated'):
                else:
                    self.pool.get('account.bank.statement.line').write(cr, uid, st_line.id, {'state': 'conciliated'})
                    aux_conciliated += st_line.amount
                    
                if (st_line.type in 'expenses' or st_line.type in 'income') and st_line.state in 'open':
                    if st_line.analytic_account_id:
                        if not st.journal_id.analytic_journal_id:
                            raise osv.except_osv(_('No Analytic Journal !'),_("You have to assign an analytic journal on the '%s' journal!") % (st.journal_id.name,))
                    if not st_line.amount:
                        continue
                    st_line_number = self.get_next_st_line_number(cr, uid, st_number, st_line, context)
                    self.create_move_from_st_line(cr, uid, st_line.id, company_currency_id, st_line_number, context)
                    
            if j_type in 'bank':
                if (aux_conciliated + st.balance_start) != st.balance_end_real:
                    raise osv.except_osv(_('Error!'),
                    _('The statement balance is incorrect !\nThe expected balance is different than the computed one.'))
            
            #~ self.write(cr, uid, [st.id], {
                    #~ 'name': st_number,
                    #~ 'balance_end_real': st.balance_end
            #~ }, context=context)
            self.write(cr, uid, [st.id], {
                    'name': st_number,
            }, context=context)
            self.log(cr, uid, st.id, _('Statement %s is confirmed, journal items are created.') % (st_number,))
        return self.write(cr, uid, ids, {'state':'confirm'}, context=context)

account_bank_statement()

