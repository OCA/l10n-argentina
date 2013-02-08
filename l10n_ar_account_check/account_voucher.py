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

from osv import osv, fields
from tools.translate import _
import netsvc


class account_voucher(osv.osv):
    '''
    Open ERP Model
    '''
    _name = 'account.voucher'
    _inherit = 'account.voucher'
    #_description = 'Change the journal_id relation kind'

    def _total_amount(self, cr, uid, ids, name, arg, context=None):
        vouchers = super(account_voucher, self)._total_amount(cr, uid, ids, name, arg, context=context)
        for v in vouchers:
            amount = 0.0
            amount_check = self._amount_checks(cr, uid, v)

            if amount_check['issued_check_amount'] != 0 :
                amount += amount_check['issued_check_amount']

            if amount_check['third_check_amount'] != 0 :
                amount += amount_check['third_check_amount']

            if amount_check['third_check_receipt_amount'] != 0 :
                amount += amount_check['third_check_receipt_amount']

            vouchers[v] += amount

        return vouchers

    _columns = {
        'issued_check_ids': fields.one2many('account.issued.check',
            'voucher_id', 'Issued Checks', required=False),
        'third_check_receipt_ids': fields.one2many('account.third.check',
            'voucher_id', 'Third Checks', required=False),
        'third_check_ids': fields.many2many('account.third.check',
            'third_check_voucher_rel', 'voucher_id', 'third_check_id',
            'Third Checks'),
        'amount': fields.function(_total_amount, method=True, type='float',  string='Paid Amount'),
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

    def onchange_pay_amount(  self, cr, uid, ids, payment_line_ids,issued_check_ids,third_check_ids,third_check_receipt_ids,
                                journal_id, partner_id, currency_id, type, date ,context=None):

        issued_pool = self.pool.get('account.issued.check')
        third_pool = self.pool.get('account.third.check')
        amount = 0.0
        res= {}
        res= super(account_voucher, self).onchange_paymode_line(cr, uid, ids, payment_line_ids, context=context)
        amount = res['value']['amount']
        
        if issued_check_ids:
            res = self.onchange_issued_checks(  cr, uid, ids, issued_check_ids,
                                                journal_id, partner_id, currency_id, type, date, context)
            amount += res['value']['amount']

        if type == 'receipt':
            if len(third_check_receipt_ids):
                res = self.onchange_third_check_receipt_ids( cr, uid, ids, third_check_receipt_ids, journal_id, 
                                                             partner_id, currency_id, type, date, context)
                amount += res['value']['amount']
        else:
            if len(third_check_ids):
                res = self.onchange_third_check_ids(cr, uid, ids, third_check_ids,
                    journal_id, partner_id, currency_id, type, date)
                amount += res['value']['amount']

        res['value']['amount'] = amount
        return res

    def onchange_issued_checks( self, cr, uid, ids, issued_check_ids,
                                journal_id, partner_id, currency_id, type, date, context=None):
    
        amount = 0.00
        
        if len(ids) < 1:
            raise osv.except_osv(_('ATENTION !'),
                    _('Save the voucher before use checks !'))
        data = {}
        for check in issued_check_ids:
            if check[2]:
                amount += check[2].get('amount', 0.00)
        data['amount'] = amount

        return {'value': data}
        

    def onchange_third_check_receipt_ids(self, cr, uid, ids,
            third_check_receipt_ids, journal_id, partner_id, currency_id, type,
            date, context=None):
        
        data = {}
        amount = 0.00
        data['amount'] = 0.0
        if not len(third_check_receipt_ids):
            return {'value': data}
        for check in third_check_receipt_ids:
            if check[1] != 0 and check[2]:
                amount += check[2]['amount']
        data['amount'] = amount
    
        return {'value': data}

    def onchange_third_check_ids(self, cr, uid, ids, third_check_ids,
            journal_id, partner_id, currency_id, type, date):
        data = {}
        amount = 0.00
        data['amount'] = 0.0
       
        third_check_ids = third_check_ids[0][2]

        if not len(third_check_ids):
            return {'value': data}

        for check_id in self.pool.get('account.third.check').browse(cr, uid, third_check_ids):
            amount += check_id.amount
        data['amount'] = amount

        return {'value': data}

    def action_move_line_create(self, cr, uid, ids, context=None):
        voucher_obj = self.pool.get('account.voucher').browse(cr, uid, ids)[0]
        wf_service = netsvc.LocalService('workflow')
        if voucher_obj.type == 'payment':
            if voucher_obj.issued_check_ids:
                for check in voucher_obj.issued_check_ids:
                    check.write({
                        'issued': True,
                        'receiving_partner_id': voucher_obj.partner_id.id,
                        'date_out': voucher_obj.date,
                    })
            if voucher_obj.third_check_ids:
                    for check in voucher_obj.third_check_ids:
                        check.write({
                            'destiny_partner_id': voucher_obj.partner_id.id,
                        })
                        wf_service.trg_validate(uid, 'account.third.check',
                                check.id, 'cartera_delivered', cr)
        elif voucher_obj.type == 'receipt':
            voucher_obj = self.pool.get('account.voucher').browse(cr, uid, ids)[0]
            for check in voucher_obj.third_check_receipt_ids:
                wf_service.trg_validate(uid, 'account.third.check', check.id, 'draft_cartera', cr)
        return super(account_voucher, self).action_move_line_create(cr, uid, ids, context=None)


    def create_move_line_hook(self, cr, uid, voucher_id, move_id, move_lines, context={}):
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

        elif v.type in ('purchase', 'payment'):
            # Cheques recibidos de terceros que los damos a un proveedor
            for check in v.third_check_ids:
                if check.amount == 0.0:
                    continue

                res = third_check_pool.create_voucher_move_line(cr, uid, check, v, context=context)
                res['move_id'] = move_id
                move_lines.append(res)

            # Cheques propios que los damos a un proveedor
            for check in v.issued_check_ids:
                if check.amount == 0.0:
                    continue

                res = issued_check_pool.create_voucher_move_line(cr, uid, check, v, context=context)
                res['move_id'] = move_id
                move_lines.append(res)

        return move_lines

    def call_issued_checks(self, cr , uid , ids , context=None):

        context['active_ids'] = ids[0]
        #view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'account.add.issued.checks.wizard.form')])
        return {
            'name':_("Add Check"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.add.issued.check',
            'src_model': 'account.add.issued.check',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
            'nodestroy': True,
            'domain': '[]',
            'context': dict(context, active_ids=ids)
            }   

    def call_third_checks(self, cr , uid , ids , context=None):

        context['active_ids'] = ids[0]
        #view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'account.add.third.checks.wizard.form')])
        return {
            'name':_("Add Check"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.add.third.check',
            'src_model': 'account.add.third.check',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
            'nodestroy': True,
            'domain': '[]',
            'context': dict(context, active_ids=ids)
            }   

account_voucher()
