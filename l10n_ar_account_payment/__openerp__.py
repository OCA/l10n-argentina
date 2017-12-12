# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2011-2014 E-MIPS (http://www.e-mips.com.ar)
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
    "name": "Payments for ARGENTINA",
    "version": "8.0.1.0.1",
    "depends": ["base", "account_voucher", "account_accountant"],
    "author": "E-MIPS,Odoo Community Association (OCA)",
    "website": "http://e-mips.com.ar",
    "license": "GPL-3",
    "category": "Own Modules",
    "description": """
    This module provide :
     Implementation of Receipt/Payments for Argentina
    """,
    'data': [
        'security/ir.model.access.csv',
        'voucher_payment_receipt_view.xml',
        'voucher_sales_purchase_view.xml',
        'account_voucher_view.xml',
        #'account_payment_view.xml',
        'payment_methods_view.xml',
        'account_journal_view.xml',
        'payment_methods_demo.xml',
    ],
    'demo': [
        'payment_methods_demo.xml',
    ],
    'installable': True,
    'active': False,
}
