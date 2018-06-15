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
    "name": "Perceptions for ARGENTINA (Percepciones) - Basic Module",
    "version": "8.0.1.0.1",
    "depends": ["l10n_ar_point_of_sale"],
    "author": "E-MIPS,Odoo Community Association (OCA)",
    "website": "http://e-mips.com.ar",
    "license": "GPL-3",
    "category": "Localisation Modules",
    "description": """
    This module provide :
    1) Implementation of Perceptions Taxes for Argentina
       based on tax objects of OpenERP like account.invoice, account.tax and account.tax.code.
    """,
    "init_xml": [
        # "perception_data.xml",
    ],
    'data': [
        # 'security/ir.model.access.csv',
        'views/perception_view.xml',
        'views/account_invoice_view.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
