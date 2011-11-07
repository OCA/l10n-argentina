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
from osv import osv, fields

class stock_picking(osv.osv):
    _name = "stock.picking"
    _inherit = "stock.picking"

    #overwrite    
    def _invoice_hook(self, cr, uid, picking, invoice_id):
        
        order_to_pick_obj = picking.sale_id
        
        if not order_to_pick_obj.fiscal_position :
            raise osv.except_osv( ('Error'),
                                  ('Check the Fiscal Position Configuration'))         
        
        # Obtengo el browse del objeto de denominacion
        denom_id = order_to_pick_obj.fiscal_position.denomination_id

        pos_ar_obj = self.pool.get('pos.ar')
        
        res_pos = pos_ar_obj.search(cr, uid,[('shop_id', '=', order_to_pick_obj.shop_id.id), ('denomination_id', '=', denom_id.id)])
        
        if not len(res_pos):
            raise osv.except_osv( ('Error'),
                                  ('You need to set up a Shop and/or a Fiscal Position')) 
        
        inv_obj = self.pool.get('account.invoice')
        vals = {'denomination_id' : denom_id.id , 'pos_ar_id': res_pos[0] }
        inv_obj.write(cr, uid, invoice_id, vals)
        
        return
        
stock_picking()
