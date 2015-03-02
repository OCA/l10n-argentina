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

from osv import osv, fields
from tools.translate import _

class account_voucher(osv.osv):
    
    _name = "account.voucher"
    _inherit = "account.voucher"
    
    _columns = {
        'statement_bank_line_ids': fields.one2many('account.bank.statement.line', 'ref_voucher_id', 'Bank statement lines'),
    }
    
    #~ def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
        #~ res = super(account_voucher, self).onchange_partner_id(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=context)
#~ 
        #~ if not partner_id:
            #~ res['value']['payment_line_ids'] = []
            #~ return res
#~ 
        #~ if not 'value' in res:
            #~ return res
#~ 
        #~ res2 = self._get_payment_lines_default_cash(cr, uid, ttype, currency_id, journal_id, context=context)
        #~ res['value']['payment_line_ids'] = res2
#~ 
        #~ return res
#~ 
    #~ def _get_payment_lines_default_cash(self, cr, uid, ttype, currency_id, journal_id, context=None):
        #~ pay_mod_pool = self.pool.get('payment.mode.receipt')
        #~ modes = pay_mod_pool.search(cr, uid, [('type', '=', ttype), ('currency','=',currency_id)])
        #~ if not modes:
            #~ return {}
#~ 
        #~ lines = []
        #~ for mode in pay_mod_pool.browse(cr, uid, modes, context=context):
            #~ if mode.journal_id and mode.journal_id.id == journal_id:
                #~ lines.append({'name': mode.name ,'amount': 0.0 ,'amount_currency':0.0 ,'payment_mode_id': mode.id, 'currency': mode.currency.id})
            #~ elif not mode.journal_id:
                #~ lines.append({'name': mode.name ,'amount': 0.0 ,'amount_currency':0.0 ,'payment_mode_id': mode.id, 'currency': mode.currency.id})
#~ 
        #~ return lines

    def proforma_voucher(self, cr, uid, ids, context=None):
        vouchers = super(account_voucher, self).proforma_voucher(cr, uid, ids, context=context)
        print 'vouchers = super(account_voucher, self).proforma_voucher(cr, uid, ids, context=context)'
        stl = []
        
        for vou in self.browse(cr, uid, ids, context=context):
            if vou.type in 'receipt':
                sign = 1
                aux_account = vou.partner_id.property_account_receivable.id
            if vou.type in 'payment':
                sign = -1
                
                aux_account = vou.partner_id.property_account_payable.id
            
            for line in vou.payment_line_ids:
                if line.payment_mode_id.journal_id and line.payment_mode_id.journal_id.type in 'cash':
                    aux_name = line.voucher_id.number
                    
                    if sign:
                        amount = line.amount * sign
                    else:
                        amount = line.amount * sign
                    
                    statement = self.pool.get('account.bank.statement').search(cr, uid, 
                    [('journal_id','=', vou.journal_id.id),('state','=','open')], order='date', limit=1)
                    
                    print statement
                    if statement:
                        statement = statement[0]
                        aux_statement = self.pool.get('account.bank.statement').browse(cr, uid, statement, context)
                        print aux_statement
                        st_line = {
                            'name': line.voucher_id.number,
                            'date': vou.date,
                            'amount': amount,
                            'account_id': aux_account,
                            'state': 'conciliated',
                            'type': vou.type,
                            'bank_statement': False,
                            'partner_id': line.voucher_id.partner_id and line.voucher_id.partner_id.id,
                            'ref_voucher_id': vou.id,
                            'creation_type': 'system',
                            'statement_id': statement,
                        }

                        st_id = self.pool.get('account.bank.statement.line').create(cr, uid, st_line, context)
                        
                    else:
                        #debe abrir una caja para ese diario
                        raise osv.except_osv(_("Validate Error!"), _("Cannot validate a voucher with cash and box not open."))

            return True
        
    def cancel_voucher(self, cr, uid, ids, vals, context=None):
        
        statement_line_obj = self.pool.get('account.bank.statement.line')
        
        for voucher in self.browse(cr, uid, ids, context=None):
            print voucher.statement_bank_line_ids
            for statement_line in voucher.statement_bank_line_ids:
                print statement_line.id
                sql = 'delete from account_bank_statement_line where id = ' + str(statement_line.id)
                cr.execute(sql)
        print context
        return super(account_voucher, self).cancel_voucher(cr, uid, ids, context=None)

account_voucher()
