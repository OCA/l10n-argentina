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
from tools.translate import _
import netsvc

class account_voucher(osv.osv):
    _name = 'account.voucher'
    _inherit = 'account.voucher'

    _columns = {
        'issued_check_ids': fields.one2many('account.issued.check',
            'voucher_id', 'Issued Checks', required=False),
        'third_check_receipt_ids': fields.one2many('account.third.check',
            'voucher_id', 'Third Checks', required=False),
        'third_check_ids': fields.many2many('account.third.check',
            'third_check_voucher_rel', 'voucher_id', 'third_check_id',
            'Third Checks'),
    }

    def _amount_checks(self, cr, uid, voucher_id):
        res = {}
        res['issued_check_amount'] = 0.00
        res['third_check_amount'] = 0.00
        res['third_check_receipt_amount'] = 0.00
        if voucher_id:
            voucher_obj = self.pool.get('account.voucher').browse(cr, uid, voucher_id)
            if voucher_obj.issued_check_ids:
                for issued_check in voucher_obj.issued_check_ids:
                    res['issued_check_amount'] += issued_check.amount
            if voucher_obj.third_check_ids:
                for third_check in voucher_obj.third_check_ids:
                    res['third_check_amount'] += third_check.amount
            if voucher_obj.third_check_receipt_ids:
                for third_rec_check in voucher_obj.third_check_receipt_ids:
                    res['third_check_receipt_amount'] += third_rec_check.amount
        return res

    def _get_issued_checks_amount(self, cr, uid, issued_check_ids, context=None):
        issued_check_obj = self.pool.get('account.issued.check')
        amount = 0.0

        for check in issued_check_ids:
            if check[0] == 4 and check[1] and not check[2]:
                am = issued_check_obj.read(cr, uid, check[1], ['amount'], context=context)['amount']
                if am:
                    amount += float(am)
            if check[2]:
                amount += check[2]['amount']

        return amount

    def _get_third_checks_amount(self, cr, uid, third_check_ids, context=None):
        third_check_obj = self.pool.get('account.third.check')
        amount = 0.0

        for check in third_check_ids:
            if check[0] == 6 and check[2]:
                for c in check[2]:
                    am = third_check_obj.read(cr, uid, c, ['amount'], context=context)['amount']
                    if am:
                        amount += float(am)

        return amount

    def _get_third_checks_receipt_amount(self, cr, uid, third_check_ids, context=None):
        third_check_obj = self.pool.get('account.third.check')
        amount = 0.0

        for check in third_check_ids:
            if check[0] == 4 and check[1] and not check[2]:
                am = third_check_obj.read(cr, uid, check[1], ['amount'], context=context)['amount']
                if am:
                    amount += float(am)
            if check[2]:
                amount += check[2]['amount']

        return amount

    def onchange_third_receipt_checks(self, cr, uid, ids, amount, payment_line_ids, third_check_receipt_ids, context=None):

        amount = self._get_payment_lines_amount(cr, uid, payment_line_ids, context)
        amount += self._get_third_checks_receipt_amount(cr, uid, third_check_receipt_ids, context)

        return {'value': {'amount': amount}}

    def onchange_payment_line(self, cr, uid, ids, amount, payment_line_ids, issued_check_ids, third_check_ids, third_check_receipt_ids, context=None):

        amount = self._get_payment_lines_amount(cr, uid, payment_line_ids, context)
        amount += self._get_issued_checks_amount(cr, uid, issued_check_ids, context)
        amount += self._get_third_checks_amount(cr, uid, third_check_ids, context)
        amount += self._get_third_checks_receipt_amount(cr, uid, third_check_receipt_ids, context)

        return {'value': {'amount': amount}}

    def onchange_issued_checks(self, cr, uid, ids, amount, payment_line_ids, issued_check_ids, third_check_ids, context=None):

        amount = self._get_payment_lines_amount(cr, uid, payment_line_ids, context)
        amount += self._get_issued_checks_amount(cr, uid, issued_check_ids, context)
        amount += self._get_third_checks_amount(cr, uid, third_check_ids, context)

        return {'value': {'amount': amount}}

    def onchange_third_checks(self, cr, uid, ids, amount, payment_line_ids, issued_check_ids, third_check_ids, context=None):

        amount = self._get_payment_lines_amount(cr, uid, payment_line_ids, context)
        amount += self._get_issued_checks_amount(cr, uid, issued_check_ids, context)
        amount += self._get_third_checks_amount(cr, uid, third_check_ids, context)

        return {'value': {'amount': amount}}

    def _hook_get_amount(self, cr, uid, ids, amount, context=None):

        print 'Hook Get amount en Cheques'
        amount = super(account_voucher, self)._hook_get_amount(cr, uid, ids, amount, context=context)

        amount_issued_checks = 0.0
        amount_third_checks = 0.0
        amount_third_receipt_checks = 0.0
        for voucher in self.browse(cr, uid, ids, context=context):
            for check in voucher.issued_check_ids:
                amount_issued_checks += check.amount
            for check in voucher.third_check_ids:
                amount_third_checks += check.amount
            for check in voucher.third_check_receipt_ids:
                amount_third_receipt_checks += check.amount

        amount += amount_issued_checks + amount_third_checks + amount_third_receipt_checks
        print 'Amount: ', amount_issued_checks, amount_third_checks, amount_third_receipt_checks, amount
        return amount

#    def action_move_line_create(self, cr, uid, ids, context=None):
#        voucher_obj = self.pool.get('account.voucher').browse(cr, uid, ids)[0]
#        wf_service = netsvc.LocalService('workflow')
#        if voucher_obj.type == 'payment':
#            if voucher_obj.issued_check_ids:
#                for check in voucher_obj.issued_check_ids:
#                    vals = {'issued': True, 'receiving_partner_id': voucher_obj.partner_id.id}
#                    if not check.issue_date:
#                        vals['issue_date'] = voucher_obj.date
#                    check.write(vals)
#
#        return super(account_voucher, self).action_move_line_create(cr, uid, ids, context=None)

    def create_move_line_hook(self, cr, uid, voucher_id, move_id, move_lines, context={}):
        wf_service = netsvc.LocalService('workflow')
        move_lines = super(account_voucher, self).create_move_line_hook(cr, uid, voucher_id, move_id, move_lines, context=context)

        third_check_pool = self.pool.get('account.third.check')
        issued_check_pool = self.pool.get('account.issued.check')

        # Voucher en cuestion que puede ser un Recibo u Orden de Pago
        v = self.browse(cr, uid, voucher_id)

        if v.type in ('sale', 'receipt'):
            for check in v.third_check_receipt_ids:
                if check.amount == 0.0:
                    continue

                res = third_check_pool.create_voucher_move_line(cr, uid, check, v, context=context)
                res['move_id'] = move_id
                move_lines.append(res)
                wf_service.trg_validate(uid, 'account.third.check', check.id, 'draft_cartera', cr)

        elif v.type in ('purchase', 'payment'):
            # Cheques recibidos de terceros que los damos a un proveedor
            for check in v.third_check_ids:
                if check.amount == 0.0:
                    continue

                res = third_check_pool.create_voucher_move_line(cr, uid, check, v, context=context)
                res['move_id'] = move_id
                move_lines.append(res)
                wf_service.trg_validate(uid, 'account.third.check', check.id, 'cartera_delivered', cr)

            # Cheques propios que los damos a un proveedor
            for check in v.issued_check_ids:
                if check.amount == 0.0:
                    continue

                res = issued_check_pool.create_voucher_move_line(cr, uid, check, v, context=context)
                res['move_id'] = move_id
                move_lines.append(res)
                vals = {'issued': True, 'receiving_partner_id': v.partner_id.id}
                if not check.issue_date:
                    vals['issue_date'] = v.date
                check.write(vals)

        return move_lines

#    def add_precreated_check(self, cr, uid, ids, context=None):
#        third_obj = self.pool.get('account.third.check')
#
#        partner_id = self.read(cr, uid, ids[0], ['partner_id'], context)['partner_id'][0]
#        # Buscamos todos los cheques de terceros del partner del voucher
#        # y que esten en estado 'draft'
#        check_ids = third_obj.search(cr, uid, [('source_partner_id','=',partner_id), ('state','=','draft'),('voucher_id','=',False)], context=context)
#
#        if check_ids:
#            third_obj.write(cr, uid, check_ids, {'voucher_id': ids[0]}, context)
#
#        return True
#
account_voucher()
