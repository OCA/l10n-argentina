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

class sale_order(models.Model):
    _name = "sale.order"
    _inherit = "sale.order"

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

sale_order()
