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
    "name" : "Argentina - Chart of Account",
    "version" : "8.0.1.0.0",
    "author" : "E-MIPS / Eynesn,Odoo Community Association (OCA)",
    "category" : "Localization/Account Charts",
    "description": 
'''
Accounting chart for Argetina in Open ERP.
''',
    "depends" : ["account_chart"],
    "demo_xml" : [],
    "update_xml" : [
        "account_tax_code.xml",
        "account_chart.xml",
        "account_tax.xml",
        #"fiscal_templates.xml",
        "l10n_chart_ar_wizard.xml"
    ],
    "active": False,
    "installable": True,
    "certificate" : "",
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

