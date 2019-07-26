###############################################################################
#
#    Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import models, api


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = "stock.picking"

    @api.model
    def _get_invoice_vals(self, key, inv_type, journal_id, move):
        res = super(StockPicking, self)._get_invoice_vals(
            key, inv_type, journal_id, move)
        if move and move.picking_id and move.picking_id.partner_id:
            res['address_shipping_id'] = move.picking_id.partner_id.id
        return res
