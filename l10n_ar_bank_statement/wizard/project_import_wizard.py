#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
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
#    Copyright 2013 E-MIPS
##############################################################################
from osv import fields, osv
from tools.translate import _

import xmlrpclib
import argparse
import sys
import os
import base64
from xml.dom import minidom
from datetime import datetime
import xlrd

from tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import date, timedelta


class project_import(osv.osv_memory):
    _name = "project.import"
    _description = "Import Project"

    _columns = {
        'filename': fields.char('Filename', size=256),
        }
        
    def read_file(self, cr, uid, ids, context=None):
        print 'read'
        aux_vou = self.pool.get('account.voucher').search(cr, uid, [('state','=','posted')], context=context) 
        #~ aux_vou = []
        stl = []
        aux_analytic = ''
        print aux_vou
        print 'f'
        for vou_id in aux_vou:
            vou = self.pool.get('account.voucher').browse(cr, uid, vou_id, context=context)
            print vou.number
            
            if vou.type in 'receipt':
                sign = 1
                aux_account = vou.partner_id.property_account_receivable.id
            if vou.type in 'payment':
                sign = -1
                
                aux_account = vou.partner_id.property_account_payable.id
            
            for line in vou.payment_line_ids:
                if line.payment_mode_id.journal_id and line.payment_mode_id.journal_id.type in 'bank':
                    aux_name = line.voucher_id.number
                    
                    if sign:
                        amount = line.amount * sign
                    else:
                        amount = line.amount * sign
                        
                    #~ aux_name = 'Linea de pago' + ' - ' + line.payment_mode_id.name
                    #~ cr.execute('select id from account_bank_statement_line where voucher_id=%s and name=%s',(line.voucher_id.id,aux_name,))
                    #~ po = cr.fetchone()
                    
                    #~ if not po:
                    st_line = {
                        'name': line.payment_mode_id.name,
                        'date': vou.date,
                        'payment_date': line.date,
                        'amount': amount,
                        'account_id': aux_account,
                        'state': 'draft',
                        'type': vou.type,
                        'bank_statement': True,
                        'partner_id': line.voucher_id.partner_id and line.voucher_id.partner_id.id,
                        'ref_voucher_id': vou.id,
                        'creation_type': 'system',
                        #~ 'ref': vou.reference,
                        'ref': vou.number,
                        'journal_id': line.payment_mode_id.journal_id.id,
                    }

                    st_id = self.pool.get('account.bank.statement.line').create(cr, uid, st_line, context)

            for check in vou.third_check_receipt_ids:
                if check.state in ('deposited'):
                    if check.type in 'common':
                        aux_payment_date = check.issue_date
                    elif check.payment_date:
                        aux_payment_date = check.payment_date
                    else:
                        aux_payment_date = deposit_date
                        
                    if check.clearing in '24':
                        aux_payment_date = date(int(aux_payment_date[0:4]),int(aux_payment_date[5:7]),int(aux_payment_date[8:10])) + timedelta(days=1)
                    elif check.clearing in '48':
                        aux_payment_date = date(int(aux_payment_date[0:4]),int(aux_payment_date[5:7]),int(aux_payment_date[8:10])) + timedelta(days=2)
                    elif check.clearing in '72':
                        aux_payment_date = date(int(aux_payment_date[0:4]),int(aux_payment_date[5:7]),int(aux_payment_date[8:10])) + timedelta(days=3)
                    
                    #~ aux_name = 'Cheque de tercero ' + check.number
                    #~ cr.execute('select id from account_bank_statement_line where voucher_id=%s and name=%s',(check.voucher_id.id,aux_name,))
                    #~ po = cr.fetchone()
                    
                    #~ if not po:
                    st_line = {
                        'name': 'Cheque de tercero ' + check.number,
                        'issue_date': check.issue_date,
                        'payment_date': aux_payment_date,
                        'amount': check.amount,
                        'account_id': check.deposit_bank_id.account_id.id,
                        'state': 'draft',
                        'type': 'receipt',
                        'bank_statement': True,
                        'partner_id': check.deposit_bank_id.partner_id.id,
                        'creation_type': 'system',
                        'ref_voucher_id': check.source_voucher_id.id,
                        'ref': check.source_voucher_id.number,
                        'journal_id': check.deposit_bank_id.journal_id.id,
                    }

                    st_id = self.pool.get('account.bank.statement.line').create(cr, uid, st_line, context)
            
            for issued_check in vou.issued_check_ids:
                if issued_check.type in 'common':
                    aux_payment_date = issued_check.issue_date
                else:
                    aux_payment_date = issued_check.payment_date
                
                #~ aux_name = 'Cheque nro ' + issued_check.number
                #~ cr.execute('select id from account_bank_statement_line where voucher_id=%s and name=%s',(issued_check.voucher_id.id,aux_name,))
                #~ po = cr.fetchone()
                
                #~ if not po:
                st_line = {
                    'name': 'Cheque nro ' + issued_check.number,
                    'issue_date': issued_check.issue_date,
                    'payment_date': aux_payment_date,
                    'amount': issued_check.amount*-1,
                    'account_id': aux_account,
                    'ref': vou.number,
                    'state': 'draft',
                    'type': 'payment',
                    'bank_statement': True,
                    'partner_id': vou.partner_id and vou.partner_id.id,
                    'ref_voucher_id': vou.id,
                    'creation_type': 'system',
                    'journal_id': issued_check.account_bank_id.journal_id.id,
                }

                st_id = self.pool.get('account.bank.statement.line').create(cr, uid, st_line, context)    

        return {'type': 'ir.actions.act_window_close'}

project_import()
