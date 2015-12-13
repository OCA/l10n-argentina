# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2011-2014 E-MIPS (http://www.e-mips.com.ar)
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

import time
from osv import osv, fields

class payment_mode_receipt_line(osv.osv):
    _name= 'payment.mode.receipt.line'
    _description= 'Payment method lines'

    def _get_company_currency(self, cr, uid, context=None):
        user_obj = self.pool.get('res.users')
        currency_obj = self.pool.get('res.currency')
        user = user_obj.browse(cr, uid, uid, context=context)

        if user.company_id:
            return user.company_id.currency_id.id
        else:
            return currency_obj.search(cr, uid, [('rate', '=', 1.0)])[0]

    _columns= {
        'name': fields.char('Mode', size=64, required=True, readonly=True, help='Payment reference'),
        'payment_mode_id': fields.many2one('account.journal', 'Payment Method', required=False, domain=[('type', 'in', ['cash', 'bank'])]),
        'amount': fields.float('Amount', digits=(16, 2), required=False, help='Payment amount in the company currency'),
        'amount_currency': fields.float('Amount in Partner Currency', digits=(16, 2), required=False, help='Payment amount in the partner currency'),
        'currency': fields.related('payment_mode_id', 'currency', type="many2one", relation='res.currency', string='Currency', store=True),
        'company_currency': fields.many2one('res.currency', 'Company Currency', readonly=False),
        'date': fields.date('Payment Date', help="This date is informative only."),
        'move_line_id': fields.many2one('account.move.line', 'Entry line', domain=[('reconcile_id', '=', False), ('account_id.type', '=', 'payable')], help='This Entry Line will be referred for the information of the ordering customer.'),
        'voucher_id' : fields.many2one('account.voucher', 'Voucher'),
    }

    # TODO: Hacer la parte de multicurrency
    _defaults = {
        'amount': 0.0,
        'company_currency': _get_company_currency,
    }

payment_mode_receipt_line()
