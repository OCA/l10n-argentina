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
    "name": "Tax Reports for Argentina",
    "version": "8.0.1.0.0",
    "depends": ["base", "account", "account_accountant",
                "sale", "purchase", "l10n_ar_chart_of_account", "l10n_ar_account_payment",
                "l10n_ar_retentions_basic", "l10n_ar_perceptions_basic"],
    "author": "E-MIPS",
    "website": "http://e-mips.com.ar",
    "license": "GPL-3",
    "category": "Localisation Modules",
    "description": """
    This module provide :
    1) Tax Report for VAT, Perceptions and Retentions
    """,
    "init_xml": [],
    'update_xml': [
        "security/ir.model.access.csv",
        # "tax_report.xml",
        "tax_report_config_view.xml",
        "wizard/account_tax_subjournal_view.xml",
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
