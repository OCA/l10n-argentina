# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2012 E-MIPS Electronica e Informatica
#                       info@e-mips.com.ar
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
    "name": "Perceptions for ARGENTINA (Percepciones) - Basic Module",
    "version": "1.0",
    "depends": ["base", "account" , "account_accountant", "sale" ,"purchase"],
    "author": "E-MIPS",
    "website": "http://e-mips.com.ar",
    "license": "GPL-3",
    "category": "Localisation Modules",
    "description": """
    This module provide :
    1) Implementation of Perceptions Taxes for Argentina
       based on tax objects of OpenERP like account.invoice, account.tax and account.tax.code.
    """,
    "init_xml": ["perception_data.xml"],
    'update_xml': [
        'security/ir.model.access.csv',
        'perception_view.xml',
        'account_invoice_view.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
