###############################################################################
#   Copyright (c) 2017-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################


from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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
    shop_id = fields.Many2one('stock.warehouse',
                              string='Warehouse',
                              required=True)
    denomination_ids = fields.Many2many('invoice.denomination',
                                        'posar_denomination_rel',
                                        'pos_ar_id', 'denomination_id',
                                        string='Denominations')
    show_in_reports = fields.Boolean('Show in reports?', default=True)
    activity_start_date = fields.Date(string="Activity Start Date",
                                      required=True)
    active = fields.Boolean('Active', default=True)
    image = fields.Binary("Image", attachment=True)

    @api.constrains('name')
    def _check_pos_name(self):
        for pos in self:
            if not (pos.name.isdigit() and len(pos.name) <= 5):
                err = _("The PoS Name should be a 4-5 digit number!")
                raise ValidationError(_("Error!\n") + err)
            if len(pos.name) < 4:
                pos.name = pos.name.zfill(4)

    @api.multi
    def name_get(self):
        res = []
        for item in self:
            name = item.name
            if item.desc:
                name += ' (%s)' % item.desc
            res.append((item.id, name))
        return res
