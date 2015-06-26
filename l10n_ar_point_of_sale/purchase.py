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

from openerp.osv import osv, fields
from openerp.tools.translate import _

class purchase_order(osv.osv):
    _name = "purchase.order"
    _inherit = "purchase.order"

    def _prepare_invoice(self, cr, uid, order, line_ids, context=None):
        fiscal_pos_obj = self.pool.get('account.fiscal.position')
        pos_ar_obj = self.pool.get('pos.ar')

        res = super(purchase_order, self)._prepare_invoice(cr, uid, order, line_ids, context)
        inv_type = res['type']

        fiscal_position_id = res['fiscal_position']
        if not fiscal_position_id:
            raise osv.except_osv(_('Error'),
                                 _('The order hasn\'t got Fiscal Position configured.')) 
        reads = fiscal_pos_obj.read(cr, uid, fiscal_position_id, ['denomination_id', 'denom_supplier_id'], context=context)

        # Es de cliente
        denomination_id = None
        pos_ar_id = None
        if inv_type in ('out_invoice', 'out_refund'):
            denomination_id = reads['denomination_id'][0]
            res_pos = pos_ar_obj.search(cr, uid,[('shop_id', '=', move.warehouse_id.id), ('denomination_id', '=', denomination_id)])
            if not res_pos:
                raise osv.except_osv( _('Error'),
                                   _('You need to set up a Point of Sale in your Warehouse')) 
            pos_ar_id = res_pos[0]
        else:
            denomination_id = reads['denom_supplier_id'][0]

        res.update({'denomination_id' : denomination_id , 'pos_ar_id': pos_ar_id})
        return res

purchase_order()
