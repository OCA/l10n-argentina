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
from openerp.tools.translate import _

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
        'journal_id':fields.many2one('account.journal', 'Journal', domain=[('type','in',('bank','cash'))], required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'date_prefered': fields.selection([
            ('now', 'Directly'),
            ('due', 'Due date'),
            ('fixed', 'Fixed date')
            ], "Preferred Date", change_default=True, required=True, states={'done': [('readonly', True)], 'open': [('readonly', True)]}, help="Choose an option for the Payment Order:'Fixed' stands for a date specified by you.'Directly' stands for the direct execution.'Due date' stands for the scheduled date of execution."),
        'line_ids': fields.one2many('payment.line', 'order_id', 'Payment lines', states={'done': [('readonly', True)], 'open': [('readonly', True)]}),
        'total_pay': fields.function(_total_pay, string="Total Pay", type='float'),
    }
 

    def unlink(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            for line in order.line_ids:
                if line.voucher_id.state=='posted':
                    raise osv.except_osv(_('Invalid Action!'), _('You cannot delete Payment Orders that has confirmed payments!'))

        return osv.osv.unlink(self, cr, uid, ids, context=context)


    def set_done(self, cr, uid, ids, *args):
        res = super(payment_order, self).set_done(cr, uid, ids, args)

        voucher_obj = self.pool.get('account.voucher')
        po_line_obj = self.pool.get('payment.line')

        for order in self.browse(cr, uid, ids):
            for line in order.line_ids:

                context = {
                    'move_line_ids': [line.move_line_id.id],
                }

                #default = voucher_obj.recompute_voucher_lines(cr, uid, [voucher_id], line.partner_id.id, order.journal_id.id, line.amount, line.currency.id, 'payment', line.date, context=context)
                default = voucher_obj.onchange_partner_id(cr, uid, [], line.partner_id.id, order.journal_id.id, line.amount, line.currency.id, 'payment', line.date, context=context)

                if 'payment_line_ids' in default['value']:
                    for payment_line in default['value']['payment_line_ids']:
                        if payment_line['payment_mode_id'] == line.mode.id:
                            payment_line['amount'] = line.amount_to_pay

                def_vals = default['value']
                line_dr_ids = [(0, 0, vals) for vals in def_vals['line_dr_ids']]
                payment_line_ids = [(0, 0, vals) for vals in def_vals['payment_line_ids']]
                voucher_vals = {
                    'name': line.name,
                    'reference': order.reference,
                    'type': 'payment',
                    'journal_id': order.journal_id.id,
                    'partner_id': line.partner_id.id,
                    'account_id': def_vals['account_id'],
                    'currency_id': def_vals['currency_id'],
                    'line_dr_ids': line_dr_ids,
                    'paid_amount_in_company_currency': def_vals['paid_amount_in_company_currency'],
                    'payment_line_ids': payment_line_ids,
                    'payment_rate': def_vals['payment_rate'],
                    'payment_rate_currency_id': def_vals['payment_rate_currency_id'],
                    'pre_line': def_vals['pre_line'],
                    'writeoff_amount': def_vals['writeoff_amount'],
                }


                res = voucher_obj.onchange_payment_line(cr, uid, ids, 0.0, payment_line_ids, context=context)
                voucher_vals['amount'] = res['value']['amount']

                voucher_id = voucher_obj.create(cr, uid, voucher_vals, context=context)
                po_line_obj.write(cr, uid, line.id, {'voucher_id': voucher_id}, context=context)
                
        return res

    def action_view_vouchers(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display vouchers created from this payment.order
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'action_vendor_payment')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]

        vou_ids = []
        for order in self.browse(cr, uid, ids, context=context):
            vou_ids += [line.voucher_id.id for line in order.line_ids]

        #choose the view_mode accordingly
        res = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_voucher_tree')
        res2 = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_payment_form')
        if len(vou_ids)>1:
            result['domain'] = "[('id','in',["+','.join(map(str, vou_ids))+"])]"
            result['views'] = [(res and res[1] or False, 'tree'), (res2 and res2[1] or False, 'form')]
        else:
            result['res_id'] = vou_ids and vou_ids[0] or False
            result['view_mode'] = "tree,form"
            result['views'] = [(res2 and res2[1] or False, 'form')]


        return result

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
        'voucher_id': fields.many2one('account.voucher', 'Voucher'),
        'amount_to_pay': fields.function(_amount_to_pay, digits_compute=dp.get_precision('Account'), string='Amount To Pay',
            store={
                'payment.line': (lambda self, cr, uid, ids, c={}: ids, ['amount_retained', 'amount_currency'], 20),
            }),
    }

payment_line()
