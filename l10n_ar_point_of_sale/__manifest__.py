###############################################################################
#
#    Copyright (c) 2018 Eynes/E-MIPS
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

{
    "name": "Point of Sale ARGENTINA",
    "category": "Accounting & Finance",
    "version": "11.0.1.0.0",
    "author": "Eynes/E-MIPS",
    "website": "http://eynes.com.ar",
    "license": "AGPL-3",
    "description": "Normativas básicas para la Facturación Argentina",  # noqa
    "depends": [
        "base",
        "sale_stock",
        "sale",
        "purchase",
        "account",
        "account_voucher",
        "base_vat_ar"
    ],
    "data": [
        'data/partner_data.xml',
        'data/iibb_situation_data.xml',
        'views/pos_ar_view.xml',
        'views/account_invoice_view.xml',
        'views/partner_view.xml',
        'views/account_view.xml',
        'views/iibb_situation_view.xml',
        'views/menuitems.xml',
        'views/res_users_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
}
