# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2011
# 
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
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from osv import osv, fields


class account_voucher(osv.osv):
    _name = "account.voucher"
    _inherit = "account.voucher"
    _columns = {
      'payment_line_ids' : fields.one2many('payment.mode.line' , 'voucher_id' , 'Payments Lines'),   
    }

    _defaults = {
        'pre_line': lambda *a: False,
    }

    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
        """price
        Returns a dict that contains new values and context

        @param partner_id: latest value from user input for field partner_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """
        default = {
            'value': {'pre_line': False},
        }

        journal_pool = self.pool.get('account.journal')
        partner_pool = self.pool.get('res.partner')

        if not partner_id:
            return default

        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        journal = journal_pool.browse(cr, uid, journal_id, context=context)

        vals = self.onchange_journal(cr, uid, ids, journal_id, [], False, partner_id, context)
        vals = vals.get('value')
        currency_id = vals.get('currency_id', currency_id)
        default = {
                'value':{'line_ids':[], 'line_dr_ids':[], 'line_cr_ids':[], 'pre_line': False, 'currency_id':currency_id},
        }

        account_id = False
        if journal.type in ('sale','sale_refund'):
            account_id = partner.property_account_receivable.id
        elif journal.type in ('purchase', 'purchase_refund','expense'):
            account_id = partner.property_account_payable.id
        else:
            account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id

        default['value']['account_id'] = account_id
        return default

    def get_invoices_and_credits(self, cr, uid, ids, context):
        line_pool = self.pool.get('account.voucher.line')
        currency_pool = self.pool.get('res.currency')
        move_line_pool = self.pool.get('account.move.line')

        ttype = context.get('type', 'receipt')

        if context is None:
            context = {}

        for v in self.browse(cr, uid, ids):

            context_multi_currency = context.copy()
            if v.date:
                context_multi_currency.update({'date': v.date})

            line_ids = ids and line_pool.search(cr, uid, [('voucher_id', '=', v.id)]) or False
            if line_ids:
                line_pool.unlink(cr, uid, line_ids)

            account_type = 'receivable'

            if ttype == 'payment':
                account_type = 'payable'
            else:
                account_type = 'receivable'

            if not context.get('move_line_ids', False):
                domain = [('state','=','valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False), ('partner_id', '=', v.partner_id.id)]
                #if context.get('invoice_id', False):
                #    domain.append(('invoice', '=', context['invoice_id']))
                ids = move_line_pool.search(cr, uid, domain, context=context)    
            else:
                ids = context['move_line_ids']
            ids.reverse()
            moves = move_line_pool.browse(cr, uid, ids, context=context)

            company_currency = v.journal_id.company_id.currency_id.id
            currency_id = v.currency_id.id
            voucher_line_ids = []
            for line in moves:
                if line.credit and line.reconcile_partial_id and ttype == 'receipt':
                    continue
                if line.debit and line.reconcile_partial_id and ttype == 'payment':
                    continue
                original_amount = line.credit or line.debit or 0.0
                amount_unreconciled = currency_pool.compute(cr, uid, line.currency_id and line.currency_id.id or company_currency, currency_id, abs(line.amount_residual_currency), context=context_multi_currency)
                rs = {
                    'name':line.move_id.name,
                    'voucher_id':v.id,
                    'type': line.credit and 'dr' or 'cr',
                    'move_line_id':line.id,
                    'account_id':line.account_id.id,
                    'amount_original': currency_pool.compute(cr, uid, line.currency_id and line.currency_id.id or company_currency, currency_id, line.currency_id and abs(line.amount_currency) or original_amount, context=context_multi_currency),
                    'date_original':line.date,
                    'date_due':line.date_maturity,
                    'amount_unreconciled': amount_unreconciled,
                }

                # Creamos las lineas del voucher
                id = line_pool.create(cr, uid, rs)
                voucher_line_ids.append(id)

            self._compute_voucher(cr, uid, v.id, voucher_line_ids, ttype, context=context_multi_currency)

        return True

    def _compute_voucher(self, cr, uid, voucher_id, voucher_line_ids, ttype, context):
        vline_obj = self.pool.get('account.voucher.line')
        move_line_obj = self.pool.get('account.move.line')
        currency_pool = self.pool.get('res.currency')

        total_credit = 0.0
        total_debit = 0.0

        v = self.browse(cr, uid, voucher_id)
        price = v.amount
        pre_line = 0
           
        if ttype == 'payment':
            total_debit = price or 0.0
        else:
            total_credit = price or 0.0

        for vline in vline_obj.browse(cr, uid, voucher_line_ids):
            rs = {}
            line = move_line_obj.browse(cr, uid, vline.move_line_id.id)

            company_currency = v.journal_id.company_id.currency_id.id
            currency_id = v.currency_id.id
            if company_currency != currency_id and ttype == 'payment':
                total_debit = currency_pool.compute(cr, uid, currency_id, company_currency, total_debit, context=context)
            elif company_currency != currency_id and ttype == 'receipt':
                total_credit = currency_pool.compute(cr, uid, currency_id, company_currency, total_credit, context=context)

 

            if line.credit and line.reconcile_partial_id and ttype == 'receipt':
                continue
            if line.debit and line.reconcile_partial_id and ttype == 'payment':
                continue
            total_credit += line.credit or 0.0
            total_debit += line.debit or 0.0
 
            if line.credit:
                amount = min(vline.amount_unreconciled, currency_pool.compute(cr, uid, company_currency, currency_id, abs(total_debit), context=context))
                rs['amount'] = amount
                total_debit -= amount
            else:
                amount = min(vline.amount_unreconciled, currency_pool.compute(cr, uid, company_currency, currency_id, abs(total_credit), context=context))
                rs['amount'] = amount
                total_credit -= amount


            vline_obj.write(cr, uid, vline.id, rs)

            line_cr_ids = []
            line_dr_ids = []
            if vline.type == 'cr':
                line_cr_ids.append(rs)
            else:
                line_dr_ids.append(rs)

            if ttype == 'payment' and len(line_cr_ids) > 0:
                pre_line = 1
            elif ttype == 'receipt' and len(line_dr_ids) > 0:
                pre_line = 1

        writeoff_amount = self._compute_writeoff_amount(cr, uid, line_dr_ids, line_cr_ids, price)

        #print 'Preline: ', v, pre_line, writeoff_amount, ttype
        self.write(cr, uid, v.id, {'pre_line':pre_line, 'writeoff_amount': writeoff_amount})

        return True

    def onchange_amount(self, cr, uid, ids, amount, context):
        #print 'onchange_amount'
        if not len(ids):
            return {}

        v = self.browse(cr, uid, ids[0])
        voucher_line_ids = [x.id for x in v.line_ids]
        #print voucher_line_ids, v.line_ids
        ttype = v.type
        self.write(cr, uid, ids[0], {'amount': amount})
        self._compute_voucher(cr, uid, v.id, voucher_line_ids, ttype, context)
        #{'value': {'line_ids': [{'amount': amount}, {'id': 1, 'amount': amount}}
        return {'value': {}}

#    def onchange_line_ids(self, cr, uid, ids, line_dr_ids, line_cr_ids, amount):
#        if not line_dr_ids and not line_cr_ids:
#            return {'value':{}}
#        line = [x[1] for x in line_dr_ids]
#        line_dr_ids = [x[2] for x in line_dr_ids]
#        line_cr_ids = [x[2] for x in line_cr_ids]
#        return {'value': {'writeoff_amount': self._compute_writeoff_amount(cr, uid, line_dr_ids, line_cr_ids, amount)}}

account_voucher()

class account_voucher_line(osv.osv):
    _name = 'account.voucher.line'
    _inherit = 'account.voucher.line'

    def delete_voucher_line(self, cr, uid, ids, context=None):
        voucher_obj = self.pool.get('account.voucher')

        id = ids[0]
        res = self.read(cr, uid, id, ['voucher_id'])
        voucher_id = res['voucher_id'][0]
        self.unlink(cr, uid, id)

        res = voucher_obj.read(cr, uid, voucher_id, ['line_ids', 'type', 'date'])
        voucher_line_ids = res['line_ids']
        ttype = res['type']

        context_multi_currency = context.copy()
        if res['date']:
            context_multi_currency.update({'date': res['date']})

        #print 'Res: ', res, ttype, voucher_line_ids
        voucher_obj._compute_voucher(cr, uid, voucher_id, voucher_line_ids, ttype, context_multi_currency)
        #voucher_obj.onchange_line_ids(cr, uid, [voucher_id], voucher_line_ids, [], 0.0)
        return True

account_voucher_line()
