#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017-TODAY Eynes - Ingenieria del software.
#    (http://www.eynes.com.ar) All Rights Reserved.
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

from openerp import api, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def _get_invoice_vals(self, key, inv_type, journal_id, move):
        """Set invoice values"""
        invoice_vals = super(StockPicking, self)._get_invoice_vals(key, inv_type, journal_id, move)
        picking = move.picking_id
        if picking.external_commerce:
            invoice_vals["dst_cuit_id"] = picking.sale_id.partner_id.wsfex_cuit_code_id.id

        return invoice_vals
