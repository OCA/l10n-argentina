##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import api, models, fields


class CheckDiscountSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    product_ids = fields.Many2many(
        comodel_name='product.product',
        relation='check_discount_settings_product_ids_rel',
        column1='check_configuration_id', column2='product_id',
        string="Concepts")

    @api.model
    def get_values(self):
        res = super().get_values()
        IrDefault = self.env['ir.default'].sudo()
        product_ids = IrDefault.get('check.discount', 'allowed_product_ids')
        res.update(
            product_ids=product_ids
        )
        return res

    @api.multi
    def set_values(self):
        super().set_values()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('check.discount', 'allowed_product_ids',
                      self.product_ids.ids)
