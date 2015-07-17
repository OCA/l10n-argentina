# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2010-2014 Eynes - Ingeniería del software All Rights Reserved
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#    All Rights Reserved. See AUTHORS for details.
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
from openerp.tools.translate import _
from datetime import datetime, date, time, timedelta

class account_voucher(osv.osv):
    _inherit = 'account.voucher'
    
    def proforma_voucher(self, cr, uid, ids, context=None):
        vouchers = super(account_voucher, self).proforma_voucher(cr, uid, ids, context=context)
        stl = []
        
        for vou in self.browse(cr, uid, ids, context=context):
            if vou.type in 'receipt':
                sign = 1
                aux_account = vou.partner_id.property_account_receivable.id
            if vou.type in 'payment':
                sign = -1
                
            for line in vou.payment_line_ids:
                if line.payment_mode_id.journal_id and line.payment_mode_id.journal_id.type not in 'bank':
                    continue

                amount = line.amount * sign
                    
                st_line = {
                    'name': vou.reference,
                    'date': line.date or vou.date,
                    'payment_date': line.date or vou.date,
                    'amount': amount,
                    'account_id': vou.partner_id.property_account_payable.id,
                    'state': 'draft',
                    'type': vou.type,
                    'partner_id': line.voucher_id.partner_id and line.voucher_id.partner_id.id,
                    'ref_voucher_id': vou.id,
                    'creation_type': 'system',
                    #~ 'ref': line.payment_mode_id.name,
                    'aux_journal_id': line.payment_mode_id.journal_id.id,
                }

                st_id = self.pool.get('account.bank.statement.line').create(cr, uid, st_line, context)
                
            for issued_check in vou.issued_check_ids:
                if issued_check.type in 'common':
                    aux_payment_date = issued_check.issue_date
                else:
                    aux_payment_date = issued_check.payment_date
                    
                st_line = {
                    'name': 'Cheque nro ' + issued_check.number,
                    'issue_date': issued_check.issue_date,
                    'payment_date': aux_payment_date,
                    'amount': issued_check.amount*-1,
                    'account_id': vou.partner_id.property_account_payable.id,
                    'ref': vou.number,
                    'state': 'draft',
                    'type': 'payment',
                    'partner_id': vou.partner_id and vou.partner_id.id,
                    'ref_voucher_id': vou.id,
                    'creation_type': 'system',
                    'ref': vou.reference,
                    'aux_journal_id': issued_check.account_bank_id.journal_id.id,
                }

                st_id = self.pool.get('account.bank.statement.line').create(cr, uid, st_line, context)

            return True
        
    def cancel_voucher(self, cr, uid, ids, vals, context=None):
        
        statement_line_obj = self.pool.get('account.bank.statement.line')
        
        for voucher in self.browse(cr, uid, ids, context=None):
            for statement_line in voucher.statement_bank_line_ids:
                if statement_line.state in 'open':
                    continue
                statement_line_obj.unlink(cr, uid, statement_line.id, context=None)
        return super(account_voucher, self).cancel_voucher(cr, uid, ids, vals, context=None)

account_voucher()
