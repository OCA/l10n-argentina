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

from odoo import models, fields
import time


class AccountAddIssuedCheck(models.Model):
    _name = 'account.add.issued.check'

    number = fields.Char(string='Check Number', size=20, required=True)
    amount = fields.Float(string='Amount Check', required=True)
    date_out = fields.Date(string='Date Issued', required=True)
    date = fields.Date(string='Date', required=True)
    debit_date = fields.Date(string='Date Out', readonly=True)
    date_changed = fields.Date(string='Date Changed', readonly=True)
    receiving_partner_id = fields.Many2one(comodel_name='res.partner',
                                           string='Receiving Entity',
                                           required=False, readonly=True)
    bank_id = fields.Many2one(comodel_name='res.bank',
                              string='Bank', required=True)
    on_order = fields.Char(string='On Order', size=64)
    signatory = fields.Char(string='Signatory', size=64)
    clearing = fields.Selection([
        ('24', '24 hs'),
        ('48', '48 hs'),
        ('72', '72 hs'),
    ], string='Clearing',
       default=lambda *a: '24')
    origin = fields.Char(string='Origin', size=64)
    account_bank_id = fields.Many2one(comodel_name='res.partner.bank',
                                      string='Destiny Account')
    payment_order_id = fields.Many2one(comodel_name='account.payment.order',
                                       string='Voucher')
    issued = fields.Boolean(string='Issued')

    def add_issued_checks(self):

        issued_check_obj = self.env['account.issued.check']
        # payment_order_id = context['active_ids'][0]
        wiz_check_obj = self.pool.get('account.add.issued.check')
        wiz_check = wiz_check_obj.browse(cr, uid, ids[0], context)
        rs = {
            'number': wiz_check.number,
            'date_out': wiz_check.date_out,
            'date': wiz_check.date,
            'bank_id': wiz_check.bank_id.id,
            'account_bank_id': wiz_check.account_bank_id.id,
            'amount': wiz_check.amount,
            'payment_order_id': payment_order_id,
        }
        check_id = issued_check_obj.create(cr, uid, rs)

        return {'type': 'ir.actions.act_window_close'}


class AccountAddThirdCheck(models.Model):

    _name = 'account.add.third.check'

    number = fields.Char(string='Check Number', size=20, required=True)
    amount = fields.Float(string='Check Amount', required=True)
    date_in = fields.Date(
        string='Date In', required=True,
        default=lambda *a: time.strftime('%Y-%m-%d'))
    date = fields.Date('Check Date', required=True)
    date_out = fields.Date('Date Out', readonly=True)
    source_partner_id = fields.Many2one(comodel_name='res.partner',
                                        string='Source Partner',
                                        required=False, readonly=True)
    destiny_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Destiny Partner',
        readonly=False, required=False,
        states={'delivered': [('required', True)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('C', 'En Cartera'),
        ('deposited', 'Deposited'),
        ('delivered', 'Delivered'),
        ('rejected', 'Rejected'),
    ], string='State', required=True,
       default=lambda *a: 'draft')
    bank_id = fields.Many2one(comodel_name='res.bank',
                              string='Bank', required=True)
    vat = fields.Char(string='Vat', size=15, required=True)
    on_order = fields.Char(string='On Order', size=64)
    signatory = fields.Char(string='Signatory', size=64)
    clearing = fields.Selection([
        ('24', '24 hs'),
        ('48', '48 hs'),
        ('72', '72 hs'),
    ], string='Clearing',
       default=lambda *a: '24')
    origin = fields.Char(string='Origen', size=64)
    account_bank_id = fields.Many2one(comodel_name='res.partner.bank',
                                      string='Destiny Account')
    payment_order_id = fields.Many2one(comodel_name='account.payment.order',
                                       string='Voucher')
    reject_debit_note = fields.Many2one(comodel_name='account.invoice',
                                        string='Reject Debit Note')

    def add_third_checks(self, cr, uid, ids, context=None):

        third_check_obj = self.pool.get('account.third.check')
        payment_order_id = context['active_ids'][0]
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
            'payment_order_id': payment_order_id,
        }
        check_id = third_check_obj.create(cr, uid, rs)
        return {'type': 'ir.actions.act_window_close'}
