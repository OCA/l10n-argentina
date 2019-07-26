##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import models, fields


class AccountFiscalPosition(models.Model):
    _name = "account.fiscal.position"
    _inherit = "account.fiscal.position"
    _description = ""

    denomination_id = fields.Many2one(
        'invoice.denomination', string='Denomination', required=True)
    denom_supplier_id = fields.Many2one(
        'invoice.denomination', string='Supplier Denomination', required=True)
    local = fields.Boolean(
        string='Local Fiscal Rules', default=True,
        help='Check this if it corresponds to apply local fiscal rules, ' +
        'like invoice number validation, etc')
