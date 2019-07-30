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
    "name": "Base Period",
    "category": "L10N AR",
    "version": "11.0.1.0.0",
    "author": "Eynes/E-MIPS",
    "license": "AGPL-3",
    "description": "Add a monthly period for accounting purposes, "
    "computed from the documents date.",
    "depends": [
        "base",
        "account",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/date_period_view.xml",
        "views/account_invoice_view.xml",
        "views/account_move_view.xml",
        "views/stock_inventory_view.xml",
        "views/menuitems.xml",
    ],
    "installable": True,
    "application": True,
}
