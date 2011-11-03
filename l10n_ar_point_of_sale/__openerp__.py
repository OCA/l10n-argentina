# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2010 Tiny SPRL (http://tiny.be). All Rights Reserved
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
    "name": "Point of Sale ARGENTINA",
    "version": "1.0",
    "depends": ["base", "sale" ,"account" ],
    "author": "E-MIPS",
    "website": "http://e-mips.com.ar",
    "license": "GPL-3",
    "category": "Own Modules",
    "description": """
    This module provide :
    1) Implementation of Point of Sale for Argentina.
    """,
    "init_xml": [],
    'update_xml': [
        'pos_ar_view.xml',
        'sale_view.xml',
        'account_invoice_view.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
