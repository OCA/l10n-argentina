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

class sale_shop(osv.osv):
    _name = "sale.shop"
    _inherit = "sale.shop"
    _columns = {
        'pos_ar_ids' : fields.one2many('pos.ar','shop_id','Points of Sales'),
    }
sale_shop()

class sale_order(osv.osv):
    _name = "sale.order"
    _inherit = "sale.order"
    

    def _make_invoice(self, cr, uid, order, lines, context=None):
        
        inv_id = super(sale_order, self)._make_invoice(cr, uid, order, lines, context)
                    
        # Browse de order                   
        sale_or_obj = self.browse(cr, uid, order)
                                                    
        # Para la denomination                              
        denom_id = sale_or_obj.fiscal_position.denomination_id
                                                                    
        # La necesitas para hacer un search de pos_ar que tengan ese shop_id
        sale_or_obj.shop_id 
                                                                  
        pos_ar_obj.search([('shop_id', '=', o.shop_id), ('denomination_id', '=', denom_id)])
        
    
    
sale_order()
