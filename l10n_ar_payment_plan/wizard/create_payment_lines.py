# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
from lxml import etree

from openerp.osv import fields, osv
from openerp.tools.translate import _

class create_move_lines(osv.osv_memory):
    _name = 'create.payment.lines'
    _description = 'Create Payment Lines Wizard'
    _columns = {
        'duedate': fields.date('Due Date', required=True),
        'entries': fields.many2many('account.move.line', 'line_payment_order_rel', 'pay_id', 'line_id', 'Entries')
    }
    _defaults = {
         'duedate': lambda *a: time.strftime('%Y-%m-%d'),
    }

#    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
#        if not context: context = {}
#        res = super(payment_order_create, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
#        if context and 'line_ids' in context:
#            doc = etree.XML(res['arch'])
#            nodes = doc.xpath("//field[@name='entries']")
#            for node in nodes:
#                node.set('domain', '[("id", "in", '+ str(context['line_ids'])+')]')
#            res['arch'] = etree.tostring(doc)
#        return res

    def create_lines(self, cr, uid, ids, context=None):
        order_obj = self.pool.get('payment.order')
        line_obj = self.pool.get('account.move.line')
        payment_obj = self.pool.get('payment.line')
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)[0]
        line_ids = [entry.id for entry in data.entries]
        if not line_ids:
            return {'type': 'ir.actions.act_window_close'}

        payment = order_obj.browse(cr, uid, context['active_id'], context=context)
        t = None
        line2bank = line_obj.line2bank(cr, uid, line_ids, t, context)

        ## Finally populate the current payment with new lines:
        for line in line_obj.browse(cr, uid, line_ids, context=context):
            if payment.date_prefered == "now":
                #no payment date => immediate payment
                date_to_pay = False
            elif payment.date_prefered == 'due':
                date_to_pay = line.date_maturity
            elif payment.date_prefered == 'fixed':
                date_to_pay = payment.date_scheduled
            payment_obj.create(cr, uid,{
                    'move_line_id': line.id,
                    'amount_currency': line.amount_residual,
                    'bank_id': line2bank.get(line.id),
                    'order_id': payment.id,
                    'partner_id': line.partner_id and line.partner_id.id or False,
                    'communication': line.ref or '/',
                    'state': line.invoice and line.invoice.reference_type != 'none' and 'structured' or 'normal',
                    'date': date_to_pay,
                    'currency': (line.invoice and line.invoice.currency_id.id) or line.journal_id.currency.id or line.journal_id.company_id.currency_id.id,
                }, context=context)
        return {'type': 'ir.actions.act_window_close'}

    def onchange_duedate(self, cr, uid, ids, duedate, context=None):
        line_obj = self.pool.get('account.move.line')

        if not context:
            context= {}

        res = {}
        if not duedate:
            return res

        # Search for move line to pay:
        domain = [('reconcile_id', '=', False), ('account_id.type', '=', 'payable'), ('amount_to_pay', '>', 0)]
        domain = domain + ['|', ('date_maturity', '<=', duedate), ('date_maturity', '=', False)]
        line_ids = line_obj.search(cr, uid, domain, context=context)
        return {'value': {'entries': line_ids} }
 
create_move_lines()


