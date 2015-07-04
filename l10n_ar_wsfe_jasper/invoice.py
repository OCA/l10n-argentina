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

from openerp import models, fields, api
from datetime import datetime

__author__ = "Sebastian Kennedy <skennedy@e-mips.com.ar>"

class account_invoice(models.Model):
    _name = "account.invoice"
    _inherit = "account.invoice"
    
    @api.one
    def _compute_bar_code(self):

        if self.type in ('in_invoice','in_refund'):
            return

        cuit = self.company_id.partner_id.vat
        pos = '0002'

        eivoucher_obj = self.env['wsfe.voucher_type']
        ei_voucher_type = eivoucher_obj.search([('document_type', '=', self.type), ('denomination_id', '=', self.denomination_id.id)])#[0]

        if self.pos_ar_id:
            pos = self.pos_ar_id.name

        #ei_voucher_type = eivoucher_obj.browse(cr, uid, aux_res)
        inv_code = ei_voucher_type.code

        if self.state == 'open' and self.cae != 'NA' and self.cae_due_date:
            cae = self.cae
            cae_due_date = datetime.strptime(self.cae_due_date, '%Y-%m-%d')
        else:
            cae_due_date = datetime.now()
            cae = '0'*14

        self.bar_code = cuit+'%02d'%int(inv_code)+pos+cae+cae_due_date.strftime('%Y%m%d')+'4'

    bar_code = fields.Char(string='Bar code', readonly=True, compute=_compute_bar_code)

account_invoice()
