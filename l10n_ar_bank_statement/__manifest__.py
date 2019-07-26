###############################################################################
#
#    Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
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
###############################################################################

{
    "name": "Bank Statement",
    "category": "L10N AR",
    "version": "11.0.1.0.2",
    "author": "Eynes/E-MIPS",
    "license": "AGPL-3",
    "description": "Manage bank statement from receipt and payment.",
    "depends": [
        'l10n_ar_account_check',
        'l10n_ar_point_of_sale',
        'account_cancel',
    ],
    "data": [
        'data/ir_sequence_data.xml',
        'wizard/pos_box_view.xml',
        'views/bank_statement_line_view.xml',
        'wizard/account_add_bank_statement_view.xml',
        'wizard/account_import_bank_statement_line_view.xml',
        'views/pos_box_concept_view.xml',
        'views/bank_statement_view.xml',
        'views/account_payment_view.xml',
        'views/account_payment_order_view.xml',
        'views/menuitems.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
    ],
    "installable": True,
    "application": True,
}
