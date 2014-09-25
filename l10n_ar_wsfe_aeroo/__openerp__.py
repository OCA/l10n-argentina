# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2014 E-MIPS (http://www.e-mips.com.ar) All Rights Reserved.
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
    "name": "WSFE Report Aeroo",
    "version": "2.0",
    "depends": ["l10n_ar_wsfe", "report_aeroo", "report_aeroo_ooo"],
    "author": "E-MIPS",
    "website": "http://e-mips.com.ar",
    "license": "GPL-3",
    "category": "Argentina Localization",
    "description": """
        Este módulo genera un reporte de Factura Electronica basada en Aeroo.
    """,
    'data': [
        'report/electronic_invoice_report.xml',
    ],
    'demo': [
        ],
    'test': [
        ],
    'installable': True,
    'active': False,
}
