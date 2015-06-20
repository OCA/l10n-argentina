# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012-2014 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
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

from openerp import models, fields, api

class invoice_denomination(models.Model):
    _name = "invoice.denomination"
    _description = "Denomination for Invoices"

    # Columnas
    # TODO: En la vista poner Placeholder 0001, 0002 o algo asi.
    # TODO: Hacer rutina que chequee que esta bien puesto
    name = fields.Selection([
            ('A','A'),
            ('B','B'),
            ('C','C'),
            ('M','M'),
            ('X','X'),
            ('E','E')], string="Denomination")
    desc = fields.Char(string="Description", required=True, size=100)
    vat_discriminated = fields.Boolean(string="Vat Discriminated in Invoices", default=False, help="If True, the vat will be discriminated at invoice report.")


class pos_ar(models.Model):
    _name = "pos.ar"
    _description = "Point of Sale for Argentina"

    name = fields.Char(string='Number', required=True, size=6)
    desc = fields.Char(string='Description', required=False, size=100)
    priority = fields.Integer(string='Priority', required=True, size=6)
    #'shop_id': fields.many2one('sale.shop', 'Shop', required=True),
    shop_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    denomination_id = fields.Many2one('invoice.denomination', string='Denomination', required=True)

    @api.multi
    def name_get(self):

        res = []
        for pos in self:
            res.append((pos.id, "%s %s" % (pos.denomination_id.name, pos.name)))

        return res

pos_ar()
