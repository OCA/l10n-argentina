# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
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

from openerp.osv import fields, osv
from openerp import netsvc

import openerp.addons.decimal_precision as dp

class payment_order(osv.osv):
    _name = 'payment.order'
    _inherit = 'payment.order'

    def _total_pay(self, cursor, user, ids, name, args, context=None):
        if not ids:
            return {}
        res = {}
        for order in self.browse(cursor, user, ids, context=context):
            if order.line_ids:
                res[order.id] = reduce(lambda x, y: x + y.amount_to_pay, order.line_ids, 0.0)
            else:
                res[order.id] = 0.0
        return res


    _columns = {
        'mode': fields.many2one('payment.mode', 'Payment Mode', select=False, required=0, states={'done': [('readonly', True)]}, help='Select the Payment Mode to be applied.'),
        'line_ids': fields.one2many('payment.line', 'order_id', 'Payment lines', states={'done': [('readonly', True)], 'open': [('readonly', True)]}),
        'total_pay': fields.function(_total_pay, string="Total Pay", type='float'),
    }
 
payment_order()

class payment_line(osv.osv):
    _name = 'payment.line'
    _inherit = 'payment.line'
 
    def _amount_to_pay(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.amount_currency - line.amount_retained

        return res

    _columns = {
        'mode': fields.many2one('payment.mode.receipt', 'Payment Mode', select=True, help='Select the Payment Mode to be applied.'),
        'amount_retained': fields.float('Amount Retained', digits_compute=dp.get_precision('Account')),
        'amount_to_pay': fields.function(_amount_to_pay, digits_compute=dp.get_precision('Account'), string='Amount To Pay',
            store={
                'payment.line': (lambda self, cr, uid, ids, c={}: ids, ['amount_retained', 'amount_currency'], 20),
            }),
    }

payment_line()
