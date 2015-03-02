# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2010-2014 Eynes - Ingeniería del software All Rights Reserved
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#    All Rights Reserved. See AUTHORS for details.
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

import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class account_bank_statement(osv.osv):
    
    _name = "account.bank.statement"
    _inherit = "account.bank.statement"
    
    def button_confirm_bank(self, cr, uid, ids, context=None):
        obj_seq = self.pool.get('ir.sequence')
        if context is None:
            context = {}

        for st in self.browse(cr, uid, ids, context=context):
            j_type = st.journal_id.type
            company_currency_id = st.journal_id.company_id.currency_id.id
            if not self.check_status_condition(cr, uid, st.state, journal_type=j_type):
                continue

            self.balance_check(cr, uid, st.id, journal_type=j_type, context=context)
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise osv.except_osv(_('Configuration Error!'),
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
                    raise osv.except_osv(_('Error!'),
                            _('The account entries lines are not in valid state.'))
            print 'lineas'
            for st_line in st.line_ids:
                if st_line.analytic_account_id:
                    if not st.journal_id.analytic_journal_id:
                        raise osv.except_osv(_('No Analytic Journal!'),_("You have to assign an analytic journal on the '%s' journal!") % (st.journal_id.name,))
                if not st_line.amount:
                    continue
                if st_line.statement_id.journal_id.type in ('cash'):
                    if st_line.type in ('expenses', 'income'):
                        st_line_number = self.get_next_st_line_number(cr, uid, st_number, st_line, context)
                        self.create_move_from_st_line(cr, uid, st_line.id, company_currency_id, st_line_number, context)
                else:
                    st_line_number = self.get_next_st_line_number(cr, uid, st_number, st_line, context)
                    self.create_move_from_st_line(cr, uid, st_line.id, company_currency_id, st_line_number, context)

            self.write(cr, uid, [st.id], {
                    'name': st_number,
                    'balance_end_real': st.balance_end
            }, context=context)
            self.message_post(cr, uid, [st.id], body=_('Statement %s confirmed, journal items were created.') % (st_number,), context=context)
        return self.write(cr, uid, ids, {'state':'confirm'}, context=context)
        
account_bank_statement()

class account_cash_statement(osv.osv):
    
    _inherit = "account.bank.statement"
    
    def button_confirm_cash(self, cr, uid, ids, context=None):
        super(account_cash_statement, self).button_confirm_bank(cr, uid, ids, context=context)
        absl_proxy = self.pool.get('account.bank.statement.line')

        TABLES = ((_('Profit'), 'profit_account_id'), (_('Loss'), 'loss_account_id'),)

        for obj in self.browse(cr, uid, ids, context=context):
            if obj.difference == 0.0:
                continue

            for item_label, item_account in TABLES:
                if getattr(obj.journal_id, item_account):
                    raise osv.except_osv(_('Error!'),
                                         _('There is no %s Account on the journal %s.') % (item_label, obj.journal_id.name,))

            is_profit = obj.difference < 0.0

            account = getattr(obj.journal_id, TABLES[is_profit][1])

            values = {
                'statement_id' : obj.id,
                'journal_id' : obj.journal_id.id,
                'account_id' : account.id,
                'amount' : obj.difference,
                'name' : 'Exceptional %s' % TABLES[is_profit][0],
            }

            absl_proxy.create(cr, uid, values, context=context)

        return self.write(cr, uid, ids, {'closing_date': time.strftime("%Y-%m-%d %H:%M:%S")}, context=context)
        
account_cash_statement()

class account_bank_statement_line(osv.osv):
    
    def _check_amount(self, cr, uid, ids, context=None):
        return True
        
    _name = "account.bank.statement.line"
    _inherit = "account.bank.statement.line"
    
    _columns = {
        'statement_id': fields.many2one('account.bank.statement', 'Statement',
            select=True, ondelete='cascade'),
        'state': fields.selection([('draft', 'Draft'),
                                   ('open','Open'),
                                   ('conciliated', 'Conciliated')],
                                   'State', required=True, readonly="1",
                                   help='When new statement is created the state will be \'Draft\'.\n'
                                        'And after getting confirmation from the bank it will be in \'Confirmed\' state.'),
        'type': fields.selection([
            ('expenses','Expenses'),
            ('income','Income'),
            ('general','General'),
            ('payment','Payment'),
            ('receipt','Receipt')
            ], 'Type', required=True),
        'ref_voucher_id': fields.many2one('account.voucher', 'Ref. voucher'),
        'bank_statement': fields.boolean('Bank statement'),
    }
    
    _defaults = {
        'state': 'draft',
        'bank_statement': True
    }

    _constraints = [
        (_check_amount, 'The amount of the voucher must be the same amount as the one on the statement line', ['amount']),
    ]

account_bank_statement_line()
    
class cash_statement_line_type(osv.osv):
    
    _name = 'cash.statement.line.type'

    _columns = {
        'type': fields.selection([('in', 'Deposit'), ('out', 'Withdrawal')], 'Type', required=True),
        'code': fields.char('Code', size=16),
        'name': fields.char('Name', size=64, required=True),
        'account_id': fields.many2one('account.account', 'Account', domain="[('type', '!=', 'view')]"),
    }

cash_statement_line_type()
