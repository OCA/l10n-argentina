##############################################################################
#
#    Copyright (C) 2004-2010 Eynes - Ingeniería del software All Rights Reserved
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "Merge addons: Bank Statements and Other Payments",
    "version": "11.0.1.0.0",
    "author": "Eynes",
    "website": "http://www.eynes.com.ar",
    "category": "Accounting",
    "description": "Add Other Payments to the Bank Statement workflow",
    "depends": [
        'l10n_ar_bank_statement',
        'l10n_ar_other_payments',
    ],
    "data": [],
    "installable": True,
    'active': False
}
