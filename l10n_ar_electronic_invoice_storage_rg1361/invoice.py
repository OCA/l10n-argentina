# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2013 E-MIPS (http://www.e-mips.com.ar) All Rights Reserved.
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
from openerp.osv import osv, fields
from openerp.tools.translate import _


class account_invoice(osv.osv):
    _name = "account.invoice"
    _inherit = "account.invoice"

    _columns = {
        'operation_code': fields.selection([('Z', 'Exports to free zone'),
                                            ('X', 'Overseas Exports'),
                                            ('E', 'Exempt Operation'),
                                            ('N', 'No Taxed Operation'),
                                            (' ', 'Internal')], 'Operation Code',
                                           required=False, help="""This code is used for SIRED. It will be set in invoices, but it could be changed."""),
    }

    def onchange_partner_id(self, cr, uid, ids, type, partner_id, date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False, context=None):

        res = super(account_invoice, self).onchange_partner_id(cr, uid, ids, type, partner_id, date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False)

        if partner_id:
            fiscal_pool = self.pool.get('account.fiscal.position')

            fiscal_position_id = res['value']['fiscal_position']

            if fiscal_position_id:
                fiscal_position = fiscal_pool.browse(cr, uid, fiscal_position_id)

                operation_code = fiscal_position.operation_code
                res['value']['operation_code'] = operation_code

        return res

account_invoice()
