# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2008-2011  Thymbra
#    Copyright (c) 2011-2014 E-MIPS (http://www.e-mips.com.ar)
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
    'name': 'Account Checks',
    'version': '8.0.1.0.0',
    'author': 'Thymbra/E-MIPS/Eynes,Odoo Community Association (OCA)',
    'description': """
    Allows to manage checks
    """,
    'category': 'Generic Modules/Accounting',
    'website': 'https://github.com/OCA/l10n-argentina',
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
        'wizard/view_check_deposit.xml',
        'account_check_view.xml',
        'account_voucher_view.xml',
        'wizard/view_check_reject.xml',
        'partner_view.xml',
    ],
    'test': [
    ],
    'active': False,
    'installable': True,
    'license': 'AGPL-3',
}
