# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2008-2011
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
from openerp.osv import osv, fields


class account_fiscal_position (osv.osv):
    _name = "account.fiscal.position"
    _inherit = "account.fiscal.position"
    _description = ""

    _columns = {
        'afip_code': fields.char('AFIP Code', size=2),
        'operation_code': fields.selection([('Z', 'Exports to free zone'),
                                            ('X', 'Overseas Exports'),
                                            ('E', 'Exempt Operation'),
                                            ('N', 'No Taxed Operation'),
                                            (' ', 'Internal')], 'Operation Code',
                                           required=False, help="""This code is used for SIRED. It will be set in invoices, but it could be changed."""),
    }

account_fiscal_position()
