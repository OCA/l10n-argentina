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

from osv import osv
from tools.translate import _

class stock_picking(osv.osv):
    _name = "stock.picking"
    _inherit = "stock.picking"

    #overwrite    
    def _invoice_hook(self, cr, uid, picking, invoice_id):

        inv_obj = self.pool.get('account.invoice')

        # Si es un picking por una venta, tambien podemos preguntar por picking.type
        if picking.sale_id:
            order_to_pick = picking.sale_id
        
            if not order_to_pick.fiscal_position :
                raise osv.except_osv( _('Error'),
                                      _('Check the Fiscal Position Configuration'))         
            
            # Obtengo el browse del objeto de denominacion
            denom_id = order_to_pick.fiscal_position.denomination_id

            pos_ar_obj = self.pool.get('pos.ar')
            
            res_pos = pos_ar_obj.search(cr, uid,[('shop_id', '=', order_to_pick.shop_id.id), ('denomination_id', '=', denom_id.id)])
            
            if not len(res_pos):
                raise osv.except_osv( _('Error'),
                                      _('You need to set up a Shop and/or a Fiscal Position')) 
            
            vals = {'denomination_id' : denom_id.id , 'pos_ar_id': res_pos[0] }
            inv_obj.write(cr, uid, invoice_id, vals)
        elif picking.purchase_id:
            order_to_pick = picking.purchase_id
        
            if not order_to_pick.fiscal_position :
                raise osv.except_osv( _('Error'),
                                      _('Check the Fiscal Position Configuration'))         
            
            # Obtengo el browse del objeto de denominacion
            denom_id = order_to_pick.fiscal_position.denom_supplier_id and order_to_pick.fiscal_position.denom_supplier_id.id
            if denom_id:
                inv_obj.write(cr, uid, invoice_id, {'denomination_id':denom_id})

        return super(stock_picking, self)._invoice_hook(cr, uid, picking, invoice_id)
    
stock_picking()
