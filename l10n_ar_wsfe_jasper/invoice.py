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
from datetime import datetime
from tools.translate import _
import pooler
import time
import re

__author__ = "Sebastian Kennedy <skennedy@e-mips.com.ar>"

class account_invoice(osv.osv):
    _name = "account.invoice"
    _inherit = "account.invoice"
    
    def _compute_bar_code(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for inv in self.browse(cr, uid, ids, context=context):
            if inv.type in ('in_invoice','in_refund'):
                continue
            cuit = inv.company_id.partner_id.vat
            pos = '0002'
            
            eivoucher_obj = self.pool.get('wsfe.voucher_type')
            aux_res = eivoucher_obj.search(cr, uid, [('document_type', '=', inv.type), ('denomination_id', '=', inv.denomination_id.id)])
            
            if aux_res:
                aux_res = aux_res[0]
            else:
                return res
                
            if inv.pos_ar_id:
                pos = inv.pos_ar_id.name

            ei_voucher_type = eivoucher_obj.browse(cr, uid, aux_res)
            inv_code = ei_voucher_type.code

            if inv.state == 'open' and inv.cae != 'NA' and inv.cae_due_date:
                cae = inv.cae
                cae_due_date = datetime.strptime(inv.cae_due_date, '%Y-%m-%d')
            else:
                cae_due_date = datetime.now()
                cae = '0'*14

            code = cuit+'%02d'%int(inv_code)+pos+cae+cae_due_date.strftime('%Y%m%d')+'4'
            
            res[inv.id] = code
        return res

    _columns = {
        'bar_code': fields.function(_compute_bar_code, string='Bar code', type='char'),
    }


   

account_invoice()
