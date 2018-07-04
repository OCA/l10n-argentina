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

    @api.model
    def _get_pos_ar(self, order, denom):
        pos_ar_obj = self.env['pos.ar']
        res_pos = pos_ar_obj.search([('shop_id', '=', order.warehouse_id.id), ('denomination_ids', 'in', denom.id)], limit=1)
        if not len(res_pos):
            raise osv.except_osv(_('Error'),
                                 _('You need to set up a Shop and/or a Fiscal Position'))

        return res_pos

    @api.model
    def _prepare_invoice(self, order, lines):

        fpos_obj = self.env['account.fiscal.position']
        res = super(sale_order, self)._prepare_invoice(order, lines)

        fiscal_position = res['fiscal_position']
        if not fiscal_position:
            raise osv.except_osv(_('Error'), _('Check the Fiscal Position Configuration. sale.order[#{0}] {1}'.format(order.id, order.name)))

        fiscal_position = fpos_obj.browse(fiscal_position)
        denom = fiscal_position.denomination_id

        pos_ar = self._get_pos_ar(order, denom)
        vals = {'denomination_id': denom.id, 'pos_ar_id': pos_ar.id}
        res.update(vals)
        return res

sale_order()
