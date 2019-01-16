###############################################################################
#   Copyright (c) 2017-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from odoo import models


class SaleOrderLineMakeInvoice(models.TransientModel):
    _name = "sale.order.line.make.invoice"
    _inherit = "sale.order.line.make.invoice"

    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        order_obj = self.pool.get('sale.order')
        res = super(SaleOrderLineMakeInvoice, self)._prepare_invoice(
            cr, uid, order, lines, context=context)

        # Denominacion
        denom_id = order.fiscal_position.denomination_id

        pos_ar_id = order_obj._get_pos_ar(cr, uid, order, denom_id,
                                          context=context)
        res['denomination_id'] = denom_id.id
        res['pos_ar_id'] = pos_ar_id.id

        return res
