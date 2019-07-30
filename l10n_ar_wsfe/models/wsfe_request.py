##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import fields, models


class WsfeRequest(models.Model):
    _name = "wsfe.request"
    _description = "WSFE Request"
    _order = "date_request desc"

    nregs = fields.Integer(string='Number of Records',
                           required=True, readonly=True)
    pos_ar = fields.Char(string='POS', required=True,
                         readonly=True, size=16)
    voucher_type = fields.Char(string='Voucher Type',
                               required=True,
                               readonly=True, size=64)
    date_request = fields.Datetime(string='Request Date', required=True)
    name = fields.Char(string='Desc', required=False, size=64)
    detail_ids = fields.One2many(comodel_name='wsfe.request.detail',
                                 inverse_name='request_id',
                                 string='Details', readonly=True)
    result = fields.Selection([('A', 'Approved'),
                               ('R', 'Rejected'),
                               ('P', 'Partial')],
                              string='Result', readonly=True)
    reprocess = fields.Boolean('Reprocess', readonly=True, default=False)
    errors = fields.Text('Errors', readonly=True)


class WsfeRequestDetail(models.Model):
    _name = "wsfe.request.detail"
    _description = "WSFE Request Detail"

    name = fields.Many2one(comodel_name='account.invoice',
                           string='Voucher', required=False,
                           readonly=True)
    request_id = fields.Many2one(comodel_name='wsfe.request',
                                 string='Request', required=True)
    concept = fields.Selection([('1', 'Products'),
                                ('2', 'Services'),
                                ('3', 'Products&Services')],
                               string='Concept', readonly=True)
    doctype = fields.Integer('Document Type', readonly=True)
    docnum = fields.Char('Document Number', size=32, readonly=True)
    voucher_number = fields.Integer('Voucher Number', readonly=True)
    voucher_date = fields.Date('Voucher Date', readonly=True)
    amount_total = fields.Char('Amount Total', size=64, readonly=True)
    cae = fields.Char('CAE', required=False, readonly=True, size=64)
    cae_duedate = fields.Date('CAE Due Date', required=False, readonly=True)
    result = fields.Selection([
        ('A', 'Approved'),
        ('R', 'Rejected')], 'Result', readonly=True)
    observations = fields.Text('Observations', readonly=True)
    errors = fields.Text('Errors', related='request_id.errors')

    currency = fields.Char('Currency', required=False, readonly=True)
    currency_rate = fields.Float('Currency Rate',
                                 required=False, readonly=True)


class WsfexRequestDetail(models.Model):
    _name = "wsfex.request.detail"
    _description = "WSFEX Request Detail"

    name = fields.Char(
        'Additional Notes', readonly=True,
        help="If you want to write down some detail about this request")
    invoice_id = fields.Many2one('account.invoice', 'Voucher',
                                 required=False, readonly=True)
    request_id = fields.Float('Request ID', readonly=True)
    voucher_number = fields.Char('Number', size=14, readonly=True)
    voucher_type_id = fields.Many2one('wsfe.voucher_type',
                                      string="OpenERP Voucher Type")
    date = fields.Date('Request Date', readonly=True)
    cae = fields.Char('CAE', required=False, readonly=True, size=64)
    cae_duedate = fields.Date('CAE Due Date', required=False, readonly=True)
    result = fields.Selection([
        ('A', 'Approved'),
        ('R', 'Rejected')], 'Result', readonly=True)
    reprocess = fields.Selection([
        ('S', 'Si'),
        ('N', 'No')], 'Reprocess', readonly=True)
    event = fields.Char('Event', size=255, readonly=True)
    error = fields.Char('Error', size=255, readonly=True)
    detail = fields.Text('Detail', readonly=True)
