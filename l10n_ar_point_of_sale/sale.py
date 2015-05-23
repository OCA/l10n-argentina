# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012-2014 E-MIPS (http://www.e-mips.com.ar)
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

from openerp import models, fields, api, _
from openerp.osv import osv
import openerp.addons.decimal_precision as dp

class sale_order_line(models.Model):
    _name = "sale.order.line"
    _inherit = "sale.order.line"

    @api.one
    @api.depends('price_unit', 'discount', 'tax_id', 'product_uom_qty',
        'product_id', 'order_id.partner_id', 'order_id.currency_id')
    def _amount_line_ar(self):
        tax_obj = self.env['account.tax']

        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = tax_obj.compute_all(price, self.product_uom_qty, self.product_id, self.order_id.partner_id)
        cur = self.order_id.pricelist_id.currency_id
        self.price_subtotal = cur.round(taxes['total'])

    # Columns
    price_subtotal = fields.Float(string='Subtotal', digits=dp.get_precision('Account'),
        store=False, readonly=True, compute='_amount_line_ar')

sale_order_line()

class sale_order(models.Model):
    _name = "sale.order"
    _inherit = "sale.order"

    @api.one
    @api.depends('order_line.price_subtotal',
                 'order_line.tax_id',
                 'order_line.discount')
    def _amount_all_ar(self):
        val = val1 = 0.0

        cur = self.pricelist_id.currency_id

        for line in self.order_line:
            val1 += line.price_subtotal
            val += self._amount_line_tax(line)

        self.amount_tax = cur.round(val)
        self.amount_untaxed = cur.round(val1)
        self.amount_total = self.amount_untaxed + self.amount_tax


    amount_untaxed = fields.Float(string='Untaxed Amount', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_amount_all_ar')
    amount_tax = fields.Float(string='Taxes', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_amount_all_ar')
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_amount_all_ar')

    @api.v7
    def _get_pos_ar(self, cr, uid, order, denom_id, context=None):

        pos_ar_obj = self.pool.get('pos.ar')
        
        if not order.fiscal_position :
            raise osv.except_osv( _('Error'),
                                  _('Check the Fiscal Position Configuration')) 
        
        res_pos = pos_ar_obj.search(cr, uid,[('shop_id', '=', order.warehouse_id.id), ('denomination_id', '=', denom_id)])
        if not len(res_pos):
            raise osv.except_osv( _('Error'),
                                  _('You need to set up a Shop and/or a Fiscal Position')) 

        return res_pos[0]

    @api.v7
    def _make_invoice(self, cr, uid, order, lines, context=None):

        invoice_id = super(sale_order, self)._make_invoice(cr, uid, order, lines, context)

        # Denominacion
        denom_id = order.fiscal_position.denomination_id
        pos_ar_id = self._get_pos_ar(cr, uid, order, denom_id.id, context=context)

        inv_obj = self.pool.get('account.invoice')
        vals = {'denomination_id' : denom_id.id , 'pos_ar_id': pos_ar_id }
        #escribo en esa invoice y retorno su id como debe ser
        inv_obj.write(cr, uid, invoice_id, vals)

        return invoice_id

#    def action_wait(self, cr, uid, ids, *args):
#        for o in self.browse(cr, uid, ids):
#            if not o.fiscal_position:
#                #TODO poner esto en un log:
#                print 'Error - No Fiscal Position Setting. Please set the Fiscal Position First'
#                #~ raise osv.except_osv(   _('No Fiscal Position Setting'),
#                                        #~ _('Please set the Fiscal Position First'))
#            if (o.order_policy == 'manual'):
#                self.write(cr, uid, [o.id], {'state': 'manual', 'date_confirm': time.strftime('%Y-%m-%d')})
#            else:
#                self.write(cr, uid, [o.id], {'state': 'progress', 'date_confirm': time.strftime('%Y-%m-%d')})
#            self.pool.get('sale.order.line').button_confirm(cr, uid, [x.id for x in o.order_line])
#            message = _("The quotation '%s' has been converted to a sales order.") % (o.name,)
#            self.log(cr, uid, o.id, message)
#        return True

    
sale_order()
