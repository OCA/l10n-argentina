###############################################################################
#   Copyright (c) 2017-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################


from odoo import fields, models


class InvoiceDenomination(models.Model):
    _name = "invoice.denomination"
    _description = "Denomination for Invoices"

    # Columnas
    # TODO: En la vista poner Placeholder 0001, 0002 o algo asi.
    # TODO: Hacer rutina que chequee que esta bien puesto
    name = fields.Selection([
            ('A', 'A'),
            ('B', 'B'),
            ('C', 'C'),
            ('M', 'M'),
            ('X', 'X'),
            ('OC', 'OC'),  # Otros comprobantes
            ('ANA', 'ANA'),
            ('E', 'E')], string="Denomination")
    desc = fields.Char(string="Description", required=True, size=100)
    vat_discriminated = fields.Boolean(string="Vat Discriminated in Invoices",
                                       default=False,
                                       help="If True, the vat will be \
                                       discriminated at invoice report.")
    pos_ar_ids = fields.Many2many('pos.ar', 'posar_denomination_rel',
                                  'denomination_id', 'pos_ar_id',
                                  string='Points of Sale', readonly=True)


class PosAr(models.Model):
    _name = "pos.ar"
    _description = "Point of Sale for Argentina"

    name = fields.Char(string='Number', required=True, size=6)
    desc = fields.Char(string='Description', required=False, size=100)
    priority = fields.Integer(string='Priority', required=True, size=6)
    # 'shop_id': fields.many2one('sale.shop', 'Shop', required=True),
    shop_id = fields.Many2one('stock.warehouse',
                              string='Warehouse',
                              required=True)
    # denomination_id = fields.Many2one('invoice.denomination',
    #                                   string='Denomination',
    #                                   required=True)
    denomination_ids = fields.Many2many('invoice.denomination',
                                        'posar_denomination_rel',
                                        'pos_ar_id', 'denomination_id',
                                        string='Denominations')
    show_in_reports = fields.Boolean('Show in reports?', default=True)
    active = fields.Boolean('Active', default=True)
