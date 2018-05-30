##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2014-2018 Aconcagua Team
#    All Rights Reserved. See AUTHORS for details.
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
##############################################################################

{
    "name": "Base VAT Ar",
    "version": "11.0.1.0.0",
    "depends": ["base", "base_vat"],
    "author": "Eynes, E-MIPS, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "VAT Modules",
    "description": "This module provides VAT Check for Argentina.",
    "data": [
        'views/partner_view.xml',
        'data/partner_data.xml',
        'security/ir.model.access.csv',
    ],
    "installable": True,
    "active": False,
}
