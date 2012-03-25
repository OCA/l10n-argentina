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
from osv import fields, osv
from tools.translate import _

class account_tax_subjournal(osv.osv_memory):
    _name = "account.tax.subjournal"
    _description = "Account Tax Subjournal Report"

    _columns = {
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal year', help='Keep empty for all open fiscal year'),
        'period': fields.many2one('account.period', 'Period'),
        }

account_tax_subjournal()
