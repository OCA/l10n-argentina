# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2011
# 
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
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################
import time
from osv import osv, fields


class payment_mode_receipt(osv.osv):
    _name= 'payment.mode.receipt'
    _description= 'Payment Mode for Receipt'
    _columns = {
        'name': fields.char('Name', size=64, required=True, help='Mode of Payment'),
        'bank_id': fields.many2one('res.partner.bank', "Bank account", required=False, help='Bank Account for the Payment Mode'),
        'account_id':fields.many2one('account.account','Account', required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'currency' : fields.many2one('res.currency', "Currency", required=True, help="The currency the field is expressed in."),
    }
    _defaults = {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id
    }

payment_mode_receipt()

class payment_mode_receipt_line(osv.osv):
    _name= 'payment.mode.receipt.line'
    _description= 'Payment mode receipt lines'
    
    def _get_currency(self, cr, uid, context=None):
        user_obj = self.pool.get('res.users')
        currency_obj = self.pool.get('res.currency')
        user = user_obj.browse(cr, uid, uid, context=context)

        if user.company_id:
            return user.company_id.currency_id.id
        else:
            return currency_obj.search(cr, uid, [('rate', '=', 1.0)])[0]
    
    def _get_date(self, cr, uid, context=None):
        if context is None:
            context = {}
        payment_order_obj = self.pool.get('payment.order')
        date = time.strftime('%Y-%m-%d')

        if context.get('order_id') and context['order_id']:
            order = payment_order_obj.browse(cr, uid, context['order_id'], context=context)
            if order.date_prefered == 'fixed':
                date = order.date_scheduled
        return date
        
    
    _columns= {
        'name': fields.char('Mode', size=64, required=True, readonly=True, help='Payment reference'),
        'payment_mode_id': fields.many2one('payment.mode.receipt', 'Payment Mode Receipt', required=False, select=True),
        'amount': fields.float('Amount', digits=(16, 2), required=False, help='Payment amount in the company currency'),
        'amount_currency': fields.float('Amount in Partner Currency', digits=(16, 2), required=False, help='Payment amount in the partner currency'),
        'currency': fields.many2one('res.currency','Partner Currency', required=False),
        'company_currency': fields.many2one('res.currency', 'Company Currency', readonly=False),
        'date': fields.date('Payment Date', help="If no payment date is specified, the bank will treat this payment line directly"),
        'move_line_id': fields.many2one('account.move.line', 'Entry line', domain=[('reconcile_id', '=', False), ('account_id.type', '=', 'payable')], help='This Entry Line will be referred for the information of the ordering customer.'),
        'voucher_id' : fields.many2one('account.voucher', 'Voucher'),
    }

    _defaults = {
        'amount': 0.0,
        'currency': _get_currency,
        'company_currency': _get_currency,
        'date': _get_date   }

payment_mode_receipt_line()
