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

from openerp import fields, models, api
from openerp.addons import decimal_precision as dp


class wsfe_request(models.Model):
    _name = "wsfe.request"
    _description = "WSFE Request"
    _order = "date_request desc"

    nregs = fields.Integer('Number of Records', required=True, readonly=True)
    pos_ar = fields.Char('POS', required=True, readonly=True, size=16)
    voucher_type = fields.Char('Voucher Type', required=True, readonly=True, size=64)
    date_request = fields.Datetime('Request Date', required=True)
    name = fields.Char('Desc', required=False, size=64)
    detail_ids = fields.One2many('wsfe.request.detail', 'request_id', 'Details', readonly=True)
    result = fields.Selection([('A', 'Approved'), ('R', 'Rejected'), ('P', 'Partial')], 'Result', readonly=True)
    reprocess = fields.Boolean('Reprocess', readonly=True, default=False)
    errors = fields.Text('Errors', readonly=True)

wsfe_request()


class wsfe_request_detail(models.Model):
    _name = "wsfe.request.detail"
    _description = "WSFE Request Detail"

    name = fields.Many2one('account.invoice', 'Voucher', required=False, readonly=True)
    request_id = fields.Many2one('wsfe.request', 'Request', required=True)
    concept = fields.Selection([('1', 'Products'), ('2', 'Services'), ('3', 'Products&Services')], 'Concept', readonly=True)
    doctype = fields.Integer('Document Type', readonly=True)
    docnum = fields.Char('Document Number', size=32, readonly=True)
    voucher_number = fields.Integer('Voucher Number', readonly=True)
    voucher_date = fields.Date('Voucher Date', readonly=True)
    amount_total = fields.Char('Amount Total', size=64, readonly=True)
    cae = fields.Char('CAE', required=False, readonly=True, size=64)
    cae_duedate = fields.Date('CAE Due Date', required=False, readonly=True)
    result = fields.Selection([('A', 'Approved'), ('R', 'Rejected')], 'Result', readonly=True)
    observations = fields.Text('Observations', readonly=True)

wsfe_request_detail()

class wsfex_request_detail(models.Model):
    _name = "wsfex.request.detail"
    _description = "WSFEX Request Detail"

    name = fields.Char('Additional Notes', size=128, readonly=True, help="If you want to write down some detail about this request")
    invoice_id = fields.Many2one('account.invoice', 'Voucher', required=False, readonly=True)
    request_id = fields.Float('Request ID', readonly=True)
    voucher_number = fields.Char('Number', size=14, readonly=True)
    voucher_type_id = fields.Many2one('wsfe.voucher_type', string="OpenERP Voucher Type")
    date = fields.Date('Request Date', readonly=True)
    cae = fields.Char('CAE', required=False, readonly=True, size=64)
    cae_duedate = fields.Date('CAE Due Date', required=False, readonly=True)
    result = fields.Selection([('A', 'Approved'),('R', 'Rejected')], 'Result', readonly=True)
    reprocess = fields.Selection([('S', 'Si'),('N', 'No')], 'Reprocess', readonly=True)
    event = fields.Char('Event', size=255, readonly=True)
    error = fields.Char('Error', size=255, readonly=True)
    detail = fields.Text('Detail', readonly=True)

wsfex_request_detail()
