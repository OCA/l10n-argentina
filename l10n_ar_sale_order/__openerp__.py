# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2013 E-MIPS (http://www.e-mips.com.ar) All Rights Reserved.
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
    "name": "Sale Order interactive",
    "version": "8.0.1.0.0",
    "depends": ["base", "sale", "sale_stock"],
    "author": "E-MIPS",
    "website": "http://e-mips.com.ar",
    "license": "GPL-3",
    "category": "Argentina Localization",
    "description": """
        Este módulo agrega la funcionalidad del calculo interactivo de importes a medida que se
        va completando una sale order.
        Requiere Odoo 8.0
    """,
    'data': [
        'sale_view.xml',
    ],
    'init_xml': [
    ],
    'test': [
    ],
    'installable': True,
    'active': False,
}
