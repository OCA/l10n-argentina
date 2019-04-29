# -*- coding: utf-8 -*-
###############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (Julian Corso)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging
import datetime

from openerp import models, api, fields, _, exceptions
# from openerp.exceptions import except_orm
# from openerp.addons.decimal_precision import decimal_precision as dp
# from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, \
#       DEFAULT_SERVER_DATETIME_FORMAT, float_compare


_logger = logging.getLogger(__name__)

class InvoiceFromBarcode(models.TransientModel):

    _name = "invoice.from.barcode"
    _description = "InvoiceFromBarcode"

    inv_number = fields.Char('Invoice Number')
    barcode = fields.Char('Barcode')
    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    type_id = fields.Many2one('wsfe.voucher_type', 'Voucher Type', readonly=True)
    pos = fields.Char('Point of Sale', readonly=True)
    cae = fields.Char('CAE', readonly=True)
    cae_due_date = fields.Date('CAE Due Date', readonly=True)

    @api.onchange('barcode')
    def _onchange_barcode(self):
        if self.barcode:
            lenn = len(self.barcode)
            if lenn == 40:
                self.partner_id = self.env['res.partner'].search([("vat", "=", self.barcode[:11]), ("parent_id", "=", False)], limit=1)
                self.type_id = self.env['wsfe.voucher_type'].search([("code", "=", str(int(self.barcode[11:13])))], limit=1)
                self.pos = self.barcode[13:17]
                self.cae = self.barcode[17:31]
                self.cae_due_date = datetime.datetime.strptime(self.barcode[31:39], '%Y%m%d')
            elif lenn == 42:
                self.partner_id = self.env['res.partner'].search([("vat", "=", self.barcode[:11]), ("parent_id", "=", False)], limit=1)
                self.type_id = self.env['wsfe.voucher_type'].search([("code", "=", str(int(self.barcode[11:14])))], limit=1)
                self.pos = self.barcode[14:19]
                self.cae = self.barcode[19:33]
                self.cae_due_date = datetime.datetime.strptime(self.barcode[33:41], '%Y%m%d')
            else:
                raise exceptions.ValidationError(_('Invalid Barcode'))
            if not self.partner_id:
                raise exceptions.ValidationError(_('Partner not found. Please create it to proceed'))
            if not self.type_id:
                raise exceptions.ValidationError(_('Invalid Invoice type'))
        else:
            self.partner_id = False
            self.type_id = False
            self.pos = False
            self.cae = False
            self.date_due = False

    @api.multi
    def generate_invoice(self):
        self._onchange_barcode()
        vals = self.env['account.invoice'].onchange_partner_id(self.type_id.document_type, self.partner_id.id)['value']
        vals['partner_id'] = self.partner_id.id
        vals['cae'] = self.cae
        vals['denomination_id'] = self.type_id.denomination_id.id
        vals['internal_number'] = self.pos + '-' + self.inv_number.zfill(8)
        vals['cae_due_date'] = self.cae_due_date
        if self.type_id.document_type == 'out_invoice':
            vals['type'] = 'in_invoice'
        elif self.type_id.document_type == 'out_refund':
            vals['type'] = 'in_refund'
        elif self.type_id.document_type == 'out_debit':
            vals['type'] = 'in_invoice'
            vals['is_debit'] = True
        new_invoice = self.env['account.invoice'].create(vals)
        return {
            'name': _('Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'res_id' : new_invoice.id,
            'view_id' : self.env.ref("account.invoice_supplier_form").id,
            'type': 'ir.actions.act_window',
            }
