# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012-2014 E-MIPS (http://www.e-mips.com.ar)
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
    "name": "base_vat_ar",
    "version": "8.0.1.0.0",
    "depends": ["base", "base_vat"],
    "author": "E-MIPS,Odoo Community Association (OCA)",
    "category": "VAT Modules",
    "description": """
    This module provide :
    * VAT Check for Argentina.
    * Modification of check_vat_routine:
        The original routine, got the VAT Number an extract the first two letters
        and used them to as Country ISO Code to know the country of the partner and to call
        the routine related to this country.
        This module modify this, getting the country from the partner itself (the ISO Code has
        to be well defined) and if this is not defined, the original routine is executed.
    """,
    'data': [
        'partner_view.xml',
        'partner_data.xml',
        'security/ir.model.access.csv',
        ],
    'demo': [],
    'installable': True,
    'active': False,
}
