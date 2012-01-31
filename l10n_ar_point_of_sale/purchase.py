# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2008-2011
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
from osv import osv
from tools.translate import _

class purchase_order(osv.osv):
    _name = "purchase.order"
    _inherit = "purchase.order"

    def action_invoice_create(self, cr, uid, ids, *args):
        invoice_obj = self.pool.get('account.invoice')

        # Llamamos a la funcion original y obtenemos el id de la invoice creada
        inv_id = super(purchase_order, self).action_invoice_create(cr, uid, ids, *args)

        # Browseamos la orden de compra
        order = self.browse(cr, uid, ids[0])

        # Si la orden no tiene un posicion fiscal, lanzamos exception
        if not order.fiscal_position :
            raise osv.except_osv( _('Error'),
                                  _('Check the Fiscal Position Configuration')) 
 
        denomination_id = order.fiscal_position.denom_supplier_id and order.fiscal_position.denom_supplier_id.id

        # Hacemos el seteo de la denomination_id
        if denomination_id:
            invoice_obj.write(cr, uid, inv_id, {'denomination_id': denomination_id})

        return inv_id

    def _invoiced_rate(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for purchase in self.browse(cursor, user, ids, context=context):
            tot = 0.0
            for invoice in purchase.invoice_ids:
                if invoice.state not in ('draft','cancel'):
                    tot += invoice.amount_total - invoice.residual
            if purchase.amount_total:
                res[purchase.id] = tot * 100.0 / purchase.amount_total
            else:
                res[purchase.id] = 0.0
        return res

purchase_order()
