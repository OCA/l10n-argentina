# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2014 e-mips.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Account Move Line(Subjournal) XLS export',
    'version': '0.6',
    'license': 'AGPL-3',
    'author': "e-mips",
    'category': 'Accounting & Finance',
    'summary': 'Journal Items Excel export',
    'depends': [
        'report_xlsx',
        'l10n_ar_point_of_sale',
        'l10n_ar_perceptions_basic',
        'l10n_ar_wsfe',
    ],
    'data': [
        "report/move_line_list_xls.xml",
        "wizard/account_tax_subjournal_view.xml",
        "security/ir.model.access.csv",
    ],
}
