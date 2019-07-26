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


class SaleAdvancePaymentInv(models.TransientModel):
    _name = "sale.advance.payment.inv"
    _inherit = "sale.advance.payment.inv"

    @api.multi
    def _prepare_advance_invoice_vals(self):
        res = super(SaleAdvancePaymentInv, self).\
            _prepare_advance_invoice_vals()
        sale_model = self.env['sale.order']
        for sale_id, inv_values in res:
            sale = sale_model.browse(sale_id)
            inv_values['address_shipping_id'] = sale.partner_shipping_id.id
        return res
