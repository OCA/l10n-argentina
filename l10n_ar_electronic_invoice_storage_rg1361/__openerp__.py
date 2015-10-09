# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2008-2011 E-MIPS Electronica e Informatica. All Rights Reserved
#                            http://www.e-mips.com.ar
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
{
    "name": "l10n_ar_electronic_invoice_storage_rg1361",
    "version": "8.0.1.0.0",
    "depends": ["l10n_ar_point_of_sale", "base_vat_ar", "l10n_ar_wsfe"],
    "author": "E-MIPS",
    "category": "Localisation/Argentina",
    "description": """
    """,
    "init_xml": [],
    'update_xml': [
        'partner_view.xml',
        'res_currency_view.xml',
        'product_view.xml',
        'account_invoice_view.xml',
        'wizard/create_sired_files_view.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
