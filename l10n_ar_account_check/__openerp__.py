# coding=utf-8

#    Copyright (C) 2008-2011  Thymbra

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

{
    'name': 'Account Checks',
    'version': '1.0',
    'author': 'E-MIPS/Eynes',
    'description': """
    Allows to manage checks
    """,
    'category': 'Generic Modules/Accounting',
    'website': 'http://www.e-mips.com.ar http://www.eynes.com.ar',
    'depends': [
        'account',
        'account_voucher',
        'l10n_ar_account_payment'
    ],
    'init_xml': [],
    'demo_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'wizard/add_checks_view.xml',
        'account_check_view.xml',
        'account_voucher_view.xml',
        'account_third_check_workflow.xml',
        'wizard/view_check_deposit.xml',
        'wizard/view_check_reject.xml',
        'partner_view.xml',
    ],
    'test': [
    ],
    'active': False,
    'installable': True,
}
