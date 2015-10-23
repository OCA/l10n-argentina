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
{
    "name": "Point of Sale ARGENTINA",
    "version": "8.0.1.1.0",
    "depends": ["base", "sale_stock", "sale" ,"purchase", "account" , "account_accountant", "base_vat_ar" ],
    "author": "E-MIPS/Proyecto Aconcagua,Odoo Community Association (OCA)",
    "website": "http://proyectoaconcagua.com.ar",
    "license": "GPL-3",
    "category": "Aconcagua",
    "description": """
    Modulo base para normativas de facturacion Argentina
    """,
    "data": [
        'partner_data.xml',
        'pos_ar_view.xml',
        #'sale_view.xml',
        'account_invoice_view.xml',
        'partner_view.xml',
        'account_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'partner_demo.xml',
        ],
    'test': [
        #'test/denomination_invoice.yml',
    ],
    'installable': True,
    'active': False,
}
