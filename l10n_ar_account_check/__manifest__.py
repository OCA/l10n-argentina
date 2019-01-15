###############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2008-2011  Thymbra
#    Copyright (c) 2012-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2014-2018 Aconcagua Team
#    All Rights Reserved. See readme/CONTRIBUTORS.rst for details.
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
###############################################################################

{
    'name': 'Account Checks',
    'version': '11.0.1.0.0',
    'author': 'Thymbra/E-MIPS/Eynes,Odoo Community Association (OCA)',
    'description': """
    Allows to manage checks
    """,
    'category': 'Generic Modules/Accounting',
    'website': 'http://www.e-mips.com.ar http://www.eynes.com.ar',
    'depends': [
        'account',
        'l10n_ar_account_payment_order',
    ],
    'data': [
        'wizard/view_check_deposit.xml',
        'wizard/view_check_reject.xml',
        'views/account_check_view.xml',
        'views/account_payment_order_view.xml',
        'views/partner_view.xml',
        'wizard/add_checks_view.xml',
        'wizard/accredit_checks_view.xml',
        'security/ir.model.access.csv',
        # TODO
        # 'data/ir_cron_data.xml',
    ],
    'installable': True,
}
