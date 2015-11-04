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
        res_pos = pos_ar_obj.search([('shop_id', '=', order.warehouse_id.id), ('denomination_id', '=', denom.id)], limit=1)
        if not len(res_pos):
            raise osv.except_osv(_('Error'),
                                 _('You need to set up a Shop and/or a Fiscal Position'))

        return res_pos

    @api.model
    def _make_invoice(self, order, lines):
        invoice_id = super(sale_order, self)._make_invoice(order, lines)

        # Denominacion
        if not order.fiscal_position:
            raise osv.except_osv(_('Error'), _('Check the Fiscal Position Configuration. sale.order[#{0}] {1}'.format(order.id, order.name)))

        denom = order.fiscal_position.denomination_id

        pos_ar = self._get_pos_ar(order, denom)

        inv_obj = self.env['account.invoice']
        vals = {'denomination_id': denom.id, 'pos_ar_id': pos_ar.id}
        # escribo en esa invoice y retorno su id como debe ser
        invoice = inv_obj.browse(invoice_id)
        invoice.write(vals)

        return invoice_id

sale_order()
