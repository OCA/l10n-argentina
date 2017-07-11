# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2017 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2017 Eynes (http://www.eynes.com.ar)
#    Copyright (c) 2017 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
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

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class sale_advance_payment_inv(osv.osv_memory):
    _name = "sale.advance.payment.inv"
    _inherit = "sale.advance.payment.inv"

    def _prepare_advance_invoice_vals(self, cr, uid, ids, context=None):

        order_obj = self.pool.get('sale.order')
        fiscal_obj = self.pool.get('account.fiscal.position')

        result = super(sale_advance_payment_inv, self)._prepare_advance_invoice_vals(
                cr, uid, ids, context=context)

        for sale_id, inv_values in result:
            order = order_obj.browse(cr, uid, sale_id, context=context)
            fiscal_position_id = inv_values['fiscal_position']
            fiscal_position = fiscal_obj.browse(cr, uid, fiscal_position_id,
                    context=context)

            # Denominacion
            denom_id = fiscal_position.denomination_id

            pos_ar_id = order_obj._get_pos_ar(cr, uid, order, denom_id.id, context=context)
            inv_values['denomination_id'] = denom_id.id
            inv_values['pos_ar_id'] = pos_ar_id
        return result
