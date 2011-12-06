
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

from osv import osv, fields


class payment_mode(osv.osv):
    _name = "payment.mode"
    _inherit = "payment.mode"
    _description= 'Payment Mode'
    _columns = {
        #'name': fields.char('Name', size=64, required=True, help='Mode of Payment'), 
        #'bank_id': fields.many2one('res.partner.bank', "Bank account", required=True,help='Bank Account for the Payment Mode'),
        #'journal': fields.many2one('account.journal', 'Journal', required=True, domain=[('type', 'in', ('bank','cash'))], help='Bank or Cash Journal for the Payment Mode'),
        'account_id' : fields.many2one( 'account.account' , 'Account' ,required=True),
    }
payment_mode()


class payment_mode_line(osv.osv):
    _name = "payment.mode.line"
    _description = 'Payment Mode Line'
    _columns = {
        'name': fields.char('Reference', size=64, required=True), 
        'payment_mode_id' : fields.many2one('payment.mode','Payment Mode'),
        'voucher_id': fields.many2one('account.voucher' , 'Voucher Reference'),
        'date': fields.date('Payment Date'),
        'amount_total' : fields.float('Amount to Pay', digits=(16, 2),required=True),
        'currency_id': fields.many2one('res.currency','Partner Currency', required=True),
        'amount_currency' : fields.float('Amount in Partner Currency', digits=(16, 2), required=True), #para pago con otra monedas
        'move_line_id': fields.many2one('account.move.line', 'Entry line', domain=[('reconcile_id', '=', False), ('account_id.type', '=', 'payable')], help='This Entry Line will be referred for the information of the ordering customer.'),
        'order_id': fields.many2one('payment.order', 'Order', required=False, ondelete='cascade', select=True),
        'dest_bank_id': fields.many2one('res.partner.bank', 'Destination Bank account'),
        'src_bank_id' : fields.many2one('res.partner.bank', 'Source Bank account'),
    }
payment_mode_line()
