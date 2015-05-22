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

sale_order()


class sale_order_line(models.Model):
    _name = 'sale.order.line'
    _inherit = 'sale.order.line'
    _description = 'Order Line'

    @api.onchange('price_unit', 'product_uom_qty', 'product_uos_qty', 'discount')
    def onchange_price_unit(self):
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = self.tax_id.compute_all(price, self.product_uom_qty, self.product_id, self.order_id.partner_id)
        currency = self.order_id.pricelist_id.currency_id.with_context(date=self.order_id.date_order or fields.Date.context_today(self.order_id))
        self.price_subtotal = currency.round(taxes['total'])

sale_order_line()

