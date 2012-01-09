# coding=utf-8

#    Copyright (C) 2008-2011  Thymbra

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
from osv import fields, osv


class account_issued_check(osv.osv):
    '''
    Account Issued Check
    '''
    _name = 'account.issued.check'
    _description = 'Manage Checks'
    _rec_name = 'number'

    _columns = {
        'number': fields.char('Check Number', size=20, required=True),
        'amount': fields.float('Amount Check', required=True),
        'date_out': fields.date('Date In', required=True),
        'date': fields.date('Date', required=True),
        'debit_date': fields.date('Date Out', readonly=True),
        'date_changed': fields.date('Date Changed', readonly=True),
        'receiving_partner_id': fields.many2one('res.partner',
            'Receiving Entity', required=False, readonly=True),
        'bank_id': fields.many2one('res.bank', 'Bank', required=True),
        'on_order': fields.char('On Order', size=64),
        'signatory': fields.char('Signatory', size=64),
        'clearing': fields.selection((
                ('24', '24 hs'),
                ('48', '48 hs'),
                ('72', '72 hs'),
            ), 'Clearing'),
        'origin': fields.char('Origin', size=64),
        'account_bank_id': fields.many2one('res.partner.bank',
            'Destiny Account'),
        'voucher_id': fields.many2one('account.voucher', 'Voucher'),
        'issued': fields.boolean('Issued'),
    }

    _defaults = {
        'clearing': lambda *a: '24',
    }
    
    def add_issued_checks(self, cr , uid , ids , context=None):
        voucher_pool = self.pool.get('account.voucher')
        voucher_ids = context['active_ids']
        
        for v in self.browse(cr, uid , voucher_ids, context):
            voucher_pool.write(cr , uid , v.id , {'issued_check_ids': [(1, ids[0] , {'voucher_id': v.id})]})
        
        return { 'type': 'ir.actions.act_window.close'} 
    


account_issued_check()


class account_third_check(osv.osv):
    '''
    Account Third Check
    '''
    _name = 'account.third.check'
    _description = 'Manage Checks'
    _rec_name = 'number'

    _columns = {
        'number': fields.char('Check Number', size=20, required=True),
        'amount': fields.float('Check Amount', required=True),
        'date_in': fields.date('Date In', required=True),
        'date': fields.date('Check Date', required=True),
        'date_out': fields.date('Date Out', readonly=True),
        'source_partner_id': fields.many2one('res.partner', 'Source Partner',
            required=False, readonly=True),
        'destiny_partner_id': fields.many2one('res.partner', 'Destiny Partner',
            readonly=False, required=False,
            states={'delivered': [('required', True)]}),
        'state': fields.selection((
                ('draft', 'Draft'),
                ('C', 'En Cartera'),
                ('deposited', 'Deposited'),
                ('delivered', 'Delivered'),
                ('rejected', 'Rejected'),
            ), 'State', required=True),
        'bank_id': fields.many2one('res.bank', 'Bank', required=True),
        'vat': fields.char('Vat', size=15, required=True),
        'on_order': fields.char('On Order', size=64),
        'signatory': fields.char('Signatory', size=64),
        'clearing': fields.selection((
                ('24', '24 hs'),
                ('48', '48 hs'),
                ('72', '72 hs'),
            ), 'Clearing'),
        'origin': fields.char('Origen', size=64),
        'account_bank_id': fields.many2one('res.partner.bank',
            'Destiny Account'),
        'voucher_id': fields.many2one('account.voucher', 'Voucher'),
        'reject_debit_note': fields.many2one('account.invoice',
            'Reject Debit Note'),
    }

    _defaults = {
        'date_in': lambda *a: time.strftime('%Y-%m-%d'),
        'state': lambda *a: 'draft',
        'clearing': lambda *a: '24',
    }

    def wkf_cartera(self, cr, uid, ids, context=None):
        # Transicion efectuada al validar un pago de cliente que contenga
        # cheques
        for check in self.browse(cr, uid, ids):
            if check.voucher_id:
                source_partner_id = check.voucher_id.partner_id.id
            else:
                source_partner_id = None
            check.write({
                'state': 'C',
                'source_partner_id': source_partner_id,
            })
        return True

    def wkf_delivered(self, cr, uid, ids, context=None):
        # Transicion efectuada al validar un pago a proveedores que entregue
        # cheques de terceros
        for check in self.browse(cr, uid, ids):
            check.write({
                'state': 'delivered',
            })
        return True

    def wkf_deposited(self, cr, uid, ids, context=None):
        # Transicion efectuada via wizard
        for check in self.browse(cr, uid, ids):
            check.write({
                'state': 'deposited',
            })
        return True

    def wkf_rejected(self, cr, uid, ids, context=None):
        for check in self.browse(cr, uid, ids):
            check.write({
                'state': 'rejected',
            })
        return True
    
    def add_third_checks(self, cr , uid , ids , context=None):
        voucher_pool = self.pool.get('account.voucher')
        voucher_ids = context['active_ids']
        
        for v in self.browse(cr, uid , voucher_ids, context):
            voucher_pool.write(cr , uid , v.id , {'third_check_receipt_ids': [(1, ids[0] , {'voucher_id': v.id})]})
            
        return {
            'type': 'ir.actions.act_window.close'
            }     

account_third_check()
