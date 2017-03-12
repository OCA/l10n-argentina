# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2013 Eynes S.R.L. (http://www.eynes.com.ar) All Rights Reserved.
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
    "name" : "Checkbook Management",
    "version" : "8.0.0.1.0",
    "author" : "eynes.com.ar,Odoo Community Association (OCA)",
    "website" : "http://eynes.com.ar/",
    "category" : "Localisation/Argentine",
    "description": """Checkbook management for Own Checks""",
    "license": "AGPL-3",
    "depends": ["base", "l10n_ar_account_check"],
    "init_xml": [],
    "data": [
        "security/ir.model.access.csv",
        "checkbook_view.xml",
        "account_voucher_view.xml",
        "wizard/create_checkbook_view.xml"
    ],
    "active": False,
    "installable": True
}
