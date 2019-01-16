###############################################################################
#   Copyright (c) 2017-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from odoo import models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = "purchase.order"

    def _prepare_invoice(self, cr, uid, order, line_ids, context=None):
        fiscal_pos_obj = self.pool.get('account.fiscal.position')
        pos_ar_obj = self.pool.get('pos.ar')

        res = super(PurchaseOrder, self)._prepare_invoice(
            cr, uid, order, line_ids, context)
        inv_type = res['type']

        fiscal_position_id = res['fiscal_position']
        if not fiscal_position_id:
            raise UserError(
                _('Error'),
                _('The order hasn\'t got Fiscal Position configured.'))

        reads = fiscal_pos_obj.read(
            cr, uid, fiscal_position_id,
            ['denomination_id', 'denom_supplier_id'],
            context=context)

        # Es de cliente
        denomination_id = None
        pos_ar_id = None
        if inv_type in ('out_invoice', 'out_refund'):
            denomination_id = reads['denomination_id'][0]
            search_list = [
                ('shop_id', '=', move.warehouse_id.id),
                ('denomination_id', '=', denomination_id)
            ]
            res_pos = pos_ar_obj.search(cr, uid, search_list)
            if not res_pos:
                raise UserError(
                    _('Error'),
                    _('You need to set up a Point of Sale in your Warehouse'))
            pos_ar_id = res_pos[0]
        else:
            denomination_id = reads['denom_supplier_id'][0]
        update_dicc = {
            'denomination_id': denomination_id,
            'pos_ar_id': pos_ar_id
        }
        res.update(update_dicc)
        return res
