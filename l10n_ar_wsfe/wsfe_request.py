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

from osv import osv, fields
import decimal_precision as dp

class wsfe_request(osv.osv):
    _name = "wsfe.request"
    _description = "WSFE Request"
    _order = "date_request desc"

    _columns = {
        'nregs' : fields.integer('Number of Records', required=True, readonly=True),
        'pos_ar' : fields.char('POS', required=True, readonly=True, size=16),
        'voucher_type' : fields.char('Voucher Type', required=True, readonly=True, size=64),
        'date_request' : fields.datetime('Request Date', required=True),
        'name' : fields.char('Desc', required=False, size=64),
        'detail_ids' : fields.one2many('wsfe.request.detail', 'request_id', 'Details', readonly=True),
        'result' : fields.selection([('A', 'Approved'),('R', 'Rejected'),('P', 'Partial')], 'Result', readonly=True),
        'reprocess' : fields.boolean('Reprocess', readonly=True),
        'errors' : fields.text('Errors', readonly=True),
    } 

    _defaults = {
        'reprocess': lambda *a: False,
        }

wsfe_request()

class wsfe_request_detail(osv.osv):
    _name = "wsfe.request.detail"
    _description = "WSFE Request Detail"

    _columns = {
        'name' : fields.many2one('account.invoice', 'Voucher', required=False, readonly=True),
        'request_id' : fields.many2one('wsfe.request', 'Request', required=True),
        'concept' : fields.selection([('1', 'Products'),('2', 'Services'),('3', 'Products&Services')], 'Concept', readonly=True),
        'doctype' : fields.integer('Document Type', readonly=True),
        'docnum' : fields.char('Document Number', size=32, readonly=True),
        'voucher_number' : fields.integer('Voucher Number', readonly=True),
        'voucher_date' : fields.date('Voucher Date', readonly=True),
        'amount_total' : fields.char('Amount Total', size=64, readonly=True),
        'cae' : fields.char('CAE', required=False, readonly=True, size=64),
        'cae_duedate' : fields.date('CAE Due Date', required=False, readonly=True),
        'result' : fields.selection([('A', 'Approved'),('R', 'Rejected')], 'Result', readonly=True),
        'observations' : fields.text('Observations', readonly=True),
    }

wsfe_request_detail()
