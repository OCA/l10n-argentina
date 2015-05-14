# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
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

import time
from openerp.osv import osv
from openerp import models, fields, api


class payment_mode_receipt(models.Model):
    _name = 'payment.mode.receipt'
    _description = 'Payment Mode for Payment/Receipt'

    name = fields.Char('Name', size=64, required=True, help='Mode of Payment')
    bank_id = fields.Many2one('res.partner.bank', "Bank account", required=False, help='Bank Account for the Payment Mode')
    account_id = fields.Many2one('account.account', 'Account', required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id.id)
    currency = fields.Many2one('res.currency', "Currency", required=True, help="The currency the field is expressed in.")
    type = fields.Selection([('payment', 'Payment'), ('receipt', 'Receipt')], 'Type', required=True)

payment_mode_receipt()


class payment_mode_receipt_line(osv.osv):
    _name = 'payment.mode.receipt.line'
    _description = 'Payment mode receipt lines'

    @api.model
    def _get_company_currency(self):
        currency_obj = self.env['res.currency']
        if self.env.user.company_id:
            return self.env.user.company_id.currency_id.id
        else:
            return currency_obj.search([('rate', '=', 1.0)], limit=1).id

    @api.model
    def _get_date(self):
        date = time.strftime('%Y-%m-%d')
        if self._context.get('order_id') and self._context['order_id']:
            payment_order_obj = self.env['payment.order']
            order = payment_order_obj.browse(self._context['order_id'])
            if order.date_prefered == 'fixed':
                date = order.date_scheduled
        return date

    name = fields.Char('Mode', size=64, required=True, readonly=True, help='Payment reference')
    payment_mode_id = fields.Many2one('payment.mode.receipt', 'Payment Mode Receipt', required=False, select=True)
    amount = fields.Float('Amount', digits=(16, 2), default=0.0, required=False, help='Payment amount in the company currency')
    amount_currency = fields.Float('Amount in Partner Currency', digits=(16, 2), required=False, help='Payment amount in the partner currency')
    currency = fields.Many2one('res.currency', 'Currency', required=False)
    company_currency = fields.Many2one('res.currency', 'Company Currency', readonly=False, default=_get_company_currency)
    date = fields.Date('Payment Date', default=_get_date, help="If no payment date is specified, the bank will treat this payment line directly")
    move_line_id = fields.Many2one('account.move.line', 'Entry line', domain=[('reconcile_id', '=', False), ('account_id.type', '=', 'payable')], help='This Entry Line will be referred for the information of the ordering customer.')
    voucher_id = fields.Many2one('account.voucher', 'Voucher')

    # TODO: Hacer la parte de multicurrency

    # _defaults = {
    #     'company_currency': _get_company_currency,
    #     'date': _get_date
    # }


payment_mode_receipt_line()

#    def onchange_amount(self, cr, uid, ids, sss, amount, voucher_amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id, context=None):
#
#        print 'ids: ', ids, sss
#        print 'voucher_amount: ', voucher_amount
#        print 'amount: ', amount
#
#        self.pool.get('account.voucher').onchange_amount(cr, uid, [], amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id, context=context)

        #return {'value': {'parent.amount': 200}}
