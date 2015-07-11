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
        if context is None:
            context = {}
        print 'button_confirm_bank CASH'

        for st in self.browse(cr, uid, ids, context=context):
            j_type = st.journal_id.type
            if not self.check_status_condition(cr, uid, st.state, journal_type=j_type):
                continue

            self.balance_check(cr, uid, st.id, journal_type=j_type, context=context)
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise osv.except_osv(_('Configuration Error!'), _('Please verify that an account is defined in the journal.'))
            for line in st.move_line_ids:
                if line.state != 'valid':
                    raise osv.except_osv(_('Error!'), _('The account entries lines are not in valid state.'))
            move_ids = []
            for st_line in st.line_ids:
                #~ compruebo los movimientos que son desde caja para generar los asientos
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
                        'analytic_account_id': st_line.analytic_id and st_line.analytic_id.id
                    }
                    #~ if st_line.analytic_id and st_line.type in 'expenses':
                        #~ vals.update({'analytic_account_id': st_line.analytic_id.id})
                        
                    self.pool.get('account.bank.statement.line').process_reconciliation(cr, uid, st_line.id, [vals], context=context)
                elif not st_line.journal_entry_id.id:
                    raise osv.except_osv(_('Error!'), _('All the account entries lines must be processed in order to close the statement.'))
                move_ids.append(st_line.journal_entry_id.id)
                #~ escribo el movimiento como conciliado
                self.pool.get('account.bank.statement.line').write(cr, uid, st_line.id, {'state': 'conciliated'}, context)
            if move_ids:
                self.pool.get('account.move').post(cr, uid, move_ids, context=context)
            self.message_post(cr, uid, [st.id], body=_('Statement %s confirmed, journal items were created.') % (st.name,), context=context)
        self.link_bank_to_partner(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'state': 'confirm', 'closing_date': time.strftime("%Y-%m-%d %H:%M:%S")}, context=context)

    def _prepare_move_line_vals(self, cr, uid, st_line, move_id, debit, credit, currency_id=False,
                amount_currency=False, account_id=False, partner_id=False, context=None):
        """Prepare the dict of values to create the move line from a
           statement line.

           :param browse_record st_line: account.bank.statement.line record to
                  create the move from.
           :param int/long move_id: ID of the account.move to link the move line
           :param float debit: debit amount of the move line
           :param float credit: credit amount of the move line
           :param int/long currency_id: ID of currency of the move line to create
           :param float amount_currency: amount of the debit/credit expressed in the currency_id
           :param int/long account_id: ID of the account to use in the move line if different
                  from the statement line account ID
           :param int/long partner_id: ID of the partner to put on the move line
           :return: dict of value to create() the account.move.line
        """
        acc_id = account_id or st_line.account_id.id
        cur_id = currency_id or st_line.statement_id.currency.id
        par_id = partner_id or (((st_line.partner_id) and st_line.partner_id.id) or False)
        vals = {
                'name': st_line.name,
                'date': st_line.date,
                'ref': st_line.ref,
                'move_id': move_id,
                'partner_id': par_id,
                'account_id': acc_id,
                'credit': credit,
                'debit': debit,
                'statement_id': st_line.statement_id.id,
                'journal_id': st_line.statement_id.journal_id.id,
                'period_id': st_line.statement_id.period_id.id,
                'currency_id': amount_currency and cur_id,
                'amount_currency': amount_currency,
        }
        #~ if st_line.analytic_id and st_line.type in 'income':
            #~ vals.update({'analytic_account_id': st_line.analytic_id.id})
            
        return vals

class account_cash_statement(osv.osv):
    
    _inherit = "account.bank.statement"
    
    def button_confirm_cash(self, cr, uid, ids, context=None):
        print 'cajero'
        absl_proxy = self.pool.get('account.bank.statement.line')

        TABLES = ((_('Profit'), 'profit_account_id'), (_('Loss'), 'loss_account_id'),)

        for obj in self.browse(cr, uid, ids, context=context):
            if obj.difference == 0.0:
                continue
            elif obj.difference < 0.0:
                account = obj.journal_id.loss_account_id
                name = _('Loss')
                if not obj.journal_id.loss_account_id:
                    raise osv.except_osv(_('Error!'), _('There is no Loss Account on the journal %s.') % (obj.journal_id.name,))
            else: # obj.difference > 0.0
                account = obj.journal_id.profit_account_id
                name = _('Profit')
                if not obj.journal_id.profit_account_id:
                    raise osv.except_osv(_('Error!'), _('There is no Profit Account on the journal %s.') % (obj.journal_id.name,))

            values = {
                'statement_id' : obj.id,
                'journal_id' : obj.journal_id.id,
                'account_id' : account.id,
                'amount' : obj.difference,
                'name' : name,
            }
            absl_proxy.create(cr, uid, values, context=context)

        return super(account_cash_statement, self).button_confirm_bank(cr, uid, ids, context=context)
        
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
        'creation_type': fields.char('Creation type', size=50, help="System: created by OpenERP, Manual: created by the user"),
        'analytic_id': fields.many2one('account.analytic.account', 'Analytic account'),
        'concept_id': fields.many2one('cash.statement.line.type', 'Concept'),
    }
    
    _defaults = {
        'state': 'draft',
        'creation_type': 'manual',
        'bank_statement': False
    }

    _constraints = [
        (_check_amount, 'The amount of the voucher must be the same amount as the one on the statement line', ['amount']),
    ]
    
    def bank_line_on_change_amount(self, cr, uid, ids, type, amount, context=None):
        """
        Force withdrawal movements to be negative and deposit ones to
        be positive.
        """
        if type == 'expenses':
            amount = -amount
        elif type == 'income':
            amount = amount

        return { 'value': { 'amount': amount } }
    
        
    #~ def unlink(self, cr, uid, ids, context=None):
        #~ for t in self.browse(cr, uid, ids, context=context):
            #~ if t.state in 'conciliated':
                #~ raise osv.except_osv(_('Invalid action !'), _('Cannot delete Account Cash Statement Line(s) which are conciliated state !'))
                #~ 
        #~ return super(account_bank_statement_line, self).unlink(cr, uid, ids, context)

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
