# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
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

from openerp.osv import osv, fields

class stock_picking(osv.osv):
    _name = "stock.picking"
    _inherit = "stock.picking"

    _columns = {
        'renum_pick_id' : fields.many2one('stock.picking.out', 'Renumerated', help="Reference to the new picking created for renumerate this one. You cannot delete pickings if it is done, so it is cancelled and a new one is created, corrected and renumerated"),
    }

    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        seq_obj = self.pool.get('ir.sequence')

        res = super(stock_picking, self).do_partial(cr, uid, ids, partial_datas, context)
        for pick_id in res:
            delivered_pick_id = res[pick_id]['delivered_picking']
            pick = self.browse(cr, uid, delivered_pick_id, context=context)

            if pick.type == 'out':
                new_pick_name = seq_obj.next_by_code(cr, uid, 'stock.picking.out.ar')
                self.write(cr, uid, delivered_pick_id, {'name': new_pick_name}, context=context)
        return res
 
stock_picking()

class stock_picking_out(osv.osv):
    _name = "stock.picking.out"
    _inherit = "stock.picking.out"

    _columns = {
        'renum_pick_id' : fields.many2one('stock.picking.out', 'Renumerated', help="Reference to the new picking created for renumerate this one. You cannot delete pickings if it is done, so it is cancelled and a new one is created, corrected and renumerated"),
    }

stock_picking_out()
