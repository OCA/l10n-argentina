# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2007-2011 E-MIPS (http://www.e-mips.com.ar)
#    All Rights Reserved. Contact: info@e-mips.com.ar
#
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
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from openerp.osv import osv, fields


class perception_perception(osv.osv):

    """Objeto que define las percepciones que pueden utilizarse

       Configura las percepciones posibles. Luego a partir de estos objetos
       se crean perception.tax que iran en las account.invoice.
       Además, se crean account_invoice_tax que serian percepciones que se realizan en ;
       una factura, ya sea, de proveedor o de cliente. Y a partir de estas se
       crean los asientos correspondientes.
       De este objeto se toma la configuracion para generar las perception.tax y
       las account.invoice.tax con datos como monto, base imponible,
       nro de certificado, etc."""
    _name = "perception.perception"
    _description = "Perception Configuration"

    _columns = {
        'name': fields.char('Perception', required=True, size=64),
        'tax_id': fields.many2one('account.tax', 'Tax', required=True, help="Tax configuration for this perception"),
        'type_tax_use': fields.related('tax_id', 'type_tax_use', type='char', string='Tax Application', readonly=True),
        'state_id': fields.many2one('res.country.state', 'State/Province'),
        'type': fields.selection([('vat', 'VAT'),
                                  ('gross_income', 'Gross Income'),
                                  ('profit', 'Profit'),
                                  ('other', 'Other')], 'Type'),
        'jurisdiccion': fields.selection([('nacional', 'Nacional'),
                                          ('provincial', 'Provincial'),
                                          ('municipal', 'Municipal')], 'Jurisdiccion'),
    }

    _defaults = {
        'jurisdiccion': 'nacional',
        'type': 'vat'
    }

perception_perception()
