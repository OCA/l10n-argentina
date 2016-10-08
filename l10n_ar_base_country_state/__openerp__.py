# -*- coding: utf-8 -*-
##############################################################################
#
#    Module for Odoo/OpenERP that adds Argentina's States (aka Provinces)
#    Copyright (C) Gabriel Davini. (<https://github.com/gabrielo77>).
#
#    This is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "Base Argentina's States (aka Provinces)",
    "version": "8.0.1.1.0",
    "depends": ["base", "account"],
    "author": "Gabriel Davini",
    "category": "Base Modules",
    "description": """
    This module provides:
        * States (aka provinces) for Argentina.
    """,
    "init_xml": [],
    'data': [
        'data/country_state_data.xml',
        'data/res_city_data.xml',
        'views/partner_view.xml',
        'views/res_city_view.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'application': True,
    'active': False,
}
