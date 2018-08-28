# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2011
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
{
    "name": "Retentions for ARGENTINA (Retenciones)",
    "version": "11.0.1.0.0",
    "depends": [
        "base",
        "account",
        "sale",
        "purchase",
        "l10n_ar_account_payment_order",
        # "l10n_ar_account_check",
    ],
    "author": "E-MIPS,Odoo Community Association (OCA)",
    "website": "http://e-mips.com.ar",
    "license": "GPL-3",
    "category": "Localisation Modules",
    "description": """
    This module provides:
    Implementation of Retentions Taxes for Argentina
    based on tax objects of OpenERP like account.tax and account.tax.code.
    """,
    'data': [
        'security/ir.model.access.csv',
        'views/retention_view.xml',
        'views/voucher_payment_receipt_view.xml',
    ],
    'installable': True,
}
