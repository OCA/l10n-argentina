# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2015 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2015 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
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

from openerp.osv import osv,fields
from tools.translate import _

class cancel_picking_done(osv.osv_memory):
    _name = 'cancel.picking.done'
    _description = 'Return Picking'
    _columns = {
        'reason' : fields.text('Reason of cancellation'),
        'next_action': fields.selection([('renumerate', 'Cancel & Create draft'), ('cancel', 'Cancel only')], 'Next Action',required=True),
    }

    def create_returns(self, cr, uid, ids, context=None):
        
        pick_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')

        # Datos del wizard
        wiz = self.browse(cr, uid, ids, context=context)[0]
        pick_ids = context['active_ids']

        # Obtenemos el picking
        new_picks = []
        for pick in pick_obj.browse(cr, uid, pick_ids, context):

            # Renumerate...clone pick
            pick_vals = {}
            if wiz.next_action == 'renumerate':
                new_pick = pick_obj.copy(cr, uid, pick.id, context=context) 
                note = _('%s\nPick renumerated from %s. %s') % (pick.note or '', pick.name, wiz.reason or '')
                pick_obj.write(cr, uid, new_pick, {'note': note}, context=context)
                new_picks.append(new_pick)
                pick_vals['renum_pick_id'] = new_pick

            # Cancelamos el picking actual y sus lineas
            moves_to_cancel = [m.id for m in pick.move_lines]
            pick_vals['state'] = 'cancel'
            pick_obj.write(cr, uid, pick.id, pick_vals, context=context)
            move_obj.write(cr, uid, moves_to_cancel, {'state': 'cancel'}, context=context)

        if new_picks:
            return self.action_view_picks(cr, uid, new_picks, context=context)

        return {'type': 'ir.actions.act_window_close'}


    def action_view_picks(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display new pickings to renumerate
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]

        #choose the view_mode accordingly
        if len(ids)>1:
            result['domain'] = "[('id','in',["+','.join(map(str, ids))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_out_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = ids and ids[0] or False
        return result

cancel_picking_done()
