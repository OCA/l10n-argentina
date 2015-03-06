# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2008-2011  Thymbra
#    Copyright (c) 2011-2014 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#    All Rights Reserved. See AUTHORS for details.
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
import time


class account_add_issued_check(osv.osv_memory):

    _name = 'account.add.issued.check'
    _columns = {
        'number': fields.char('Check Number', size=20, required=True),
        'amount': fields.float('Amount Check', required=True),
        'date_out': fields.date('Date Issued', required=True),
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

    def add_issued_checks(self, cr, uid, ids, context=None):

        issued_check_obj = self.pool.get('account.issued.check')
        voucher_id = context['active_ids'][0]
        wiz_check_obj = self.pool.get('account.add.issued.check')
        wiz_check = wiz_check_obj.browse(cr, uid, ids[0], context)
        rs = {
            'number': wiz_check.number,
            'date_out': wiz_check.date_out,
            'date': wiz_check.date,
            'bank_id': wiz_check.bank_id.id,
            'account_bank_id': wiz_check.account_bank_id.id,
            'amount': wiz_check.amount,
            'voucher_id': voucher_id,
        }
        check_id = issued_check_obj.create(cr, uid, rs)

        return {'type': 'ir.actions.act_window_close'}

account_add_issued_check()


class account_add_third_check(osv.osv_memory):

    _name = 'account.add.third.check'
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

    def add_third_checks(self, cr, uid, ids, context=None):

        third_check_obj = self.pool.get('account.third.check')
        voucher_id = context['active_ids'][0]
        wiz_check_obj = self.pool.get('account.add.third.check')
        wiz_check = wiz_check_obj.browse(cr, uid, ids[0], context)
        rs = {
            'number': wiz_check.number,
            'amount': wiz_check.amount,
            'date_in': wiz_check.date_in,
            'date': wiz_check.date,
            'vat': wiz_check.vat,
            'bank_id': wiz_check.bank_id.id,
            'clearing': wiz_check.clearing,
            'account_bank_id': wiz_check.account_bank_id.id,
            'voucher_id': voucher_id,
        }
        check_id = third_check_obj.create(cr, uid, rs)
        return {'type': 'ir.actions.act_window_close'}

account_add_third_check()
