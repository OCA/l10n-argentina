# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011-2012 E-MIPS Electronica e Informatica
#               All Rights Reserved (<http://www.e-mips.com.ar>).
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
from openerp import models, fields, api
from openerp.tools.translate import _


class sale_order(models.Model):
    _name = "sale.order"
    _description = "Sales Order"
    _inherit = "sale.order"
    _order = "date_order desc, name desc"

    amount_untaxed = fields.Float(compute='_compute_amount_all')
    amount_tax = fields.Float(compute='_compute_amount_all')
    amount_total = fields.Float(compute='_compute_amount_all')

    @api.depends('order_line.price_subtotal')
    def _compute_amount_all(self):
        for order in self:
            amount_tax = amount_untaxed = 0.0
            currency = order.pricelist_id.currency_id.with_context(date=order.date_order or fields.Date.context_today(order))
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += self._amount_line_tax(line)
            order.amount_tax = currency.round(amount_tax)
            order.amount_untaxed = currency.round(amount_untaxed)
            order.amount_total = currency.round(amount_tax + amount_untaxed)

sale_order()


class sale_order_line(models.Model):
    _name = 'sale.order.line'
    _inherit = 'sale.order.line'
    _description = 'Order Line'

    price_subtotal = fields.Float(compute='_compute_price_subtotal')

    @api.depends('price_unit', 'product_uom_qty', 'product_uos_qty', 'discount')
    def _compute_price_subtotal(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
            currency = line.order_id.pricelist_id.currency_id.with_context(date=line.order_id.date_order or fields.Date.context_today(line.order_id))
            line.price_subtotal = currency.round(taxes['total'])

sale_order_line()

