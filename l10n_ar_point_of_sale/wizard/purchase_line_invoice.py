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

from openerp.osv import osv
from openerp.tools.translate import _


class purchase_line_invoice(osv.osv_memory):
    _name = 'purchase.order.line_invoice'
    _inherit = 'purchase.order.line_invoice'

    def makeInvoices(self, cr, uid, ids, context=None):
        inv_obj = self.pool.get('account.invoice')
        fiscal_pos_obj = self.pool.get('account.fiscal.position')

        res = super(purchase_line_invoice, self).makeInvoices(cr, uid, ids, context)
        invoice_ids = eval(res['domain'])[0][2]

        for invoice_id in invoice_ids:
            fiscal_position_id = inv_obj.read(cr, uid, invoice_id, ['fiscal_position'])['fiscal_position']
            if not fiscal_position_id:
                raise osv.except_osv(_("Error"), _("Please set Fiscal Position in order"))

            reads = fiscal_pos_obj.read(cr, uid, fiscal_position_id[0], ['denom_supplier_id'], context=context)
            denomination_id = reads['denom_supplier_id'][0]

            inv_obj.write(cr, uid, invoice_id, {'denomination_id' : denomination_id})

        return res 

purchase_line_invoice()
