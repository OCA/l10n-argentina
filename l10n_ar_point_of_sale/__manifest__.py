###############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2014-2018 Aconcagua Team
#    All Rights Reserved. See readme/CONTRIBUTORS.rst for details.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
{
    "name": "Point of Sale ARGENTINA",
    "version": "11.0.1.0.0",
    "depends": [
        "base",
        "sale_stock",
        "sale",
        "purchase",
        "account",
        "account_voucher",
        "base_vat_ar"
    ],
    "author": "Eynes, E-MIPS, Proyecto Aconcagua, \
        Odoo Community Association (OCA)",
    "license": "GPL-3",
    "category": "Aconcagua",
    "description": """
    Modulo base para normativas de facturacion Argentina
    """,
    "data": [
        'data/partner_data.xml',
        'views/pos_ar_view.xml',
        'views/account_invoice_view.xml',
        'views/partner_view.xml',
        'views/account_view.xml',
        'views/menuitems.xml',
        'security/ir.model.access.csv',
    ],
    'test': [
        # 'test/denomination_invoice.yml',
    ],
    'installable': True,
    'active': False,
}
