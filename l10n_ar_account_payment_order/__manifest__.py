###############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
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
    "name": "Payment Order",
    "category": "Accounting & Finance",
    "version": "11.0.1.0.0",
    "author": "Eynes/E-MIPS",
    "license": "AGPL-3",
    "description": "Module Description",
    "depends": [
        "base",
        "account",
        "analytic",
        "base_period",
    ],
    "data": [
        "views/assets.xml",
        "views/account_payment_order_receipt_view.xml",
        "views/account_journal_view.xml",
        # "views/account_invoice.xml",  # TODO
        "security/payment_rule.xml",
        "security/ir.model.access.csv",
    ],
    "qweb": ['static/src/xml/*.xml'],
    "installable": True,
    "application": True,
}
