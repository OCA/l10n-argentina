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
    
    def _total_amount(self, cr, uid, ids, name, arg, context=None):
        print '**Total Amount'
        pay_line_pool = self.pool.get('payment.mode.receipt.line')
        res = {}
        for v in self.browse(cr, uid , ids, context):
            amount = 0.0
            payment_lines = pay_line_pool.search(cr, uid, [('voucher_id','=', v.id)] )
            for line in pay_line_pool.browse(cr, uid, payment_lines, context):
                if not line.amount:
                    continue
                amount += line.amount  
            res[v.id] = amount

        return res
    
    _name = "account.voucher"
    _inherit = "account.voucher"
    _columns = {
      'payment_line_ids': fields.one2many('payment.mode.receipt.line' , 'voucher_id' , 'Payments Lines'),
      'amount': fields.function(_total_amount, method=True, type='float',  string='Paid Amount'),
    }

    def _get_payment_lines_default(self, cr, uid, context=None):
        print '***_get_payment_lines_default***'
        pay_mod_pool = self.pool.get('payment.mode.receipt')
        modes = pay_mod_pool.search(cr, uid, [])
        lines = []
        for mode in pay_mod_pool.browse(cr, uid, modes, context=context):
            lines.append({'name': mode.name ,'amount': 0.0 ,'amount_currency':0.0 ,'payment_mode_id': mode.id})
            print mode.name
        return lines

    _defaults = {
        'pre_line': lambda *a: False,
        #'payment_line_ids': _get_payment_lines_default,
    }

    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
        """
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

        if not journal_id:
            return default

        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        vals = self.onchange_journal(cr, uid, ids, journal_id, [], False, partner_id, context)
        vals = vals.get('value')
        currency_id = vals.get('currency_id', currency_id)
        default = {
                'value':{'line_ids':[], 'line_dr_ids':[], 'line_cr_ids':[], 'pre_line': False, 'currency_id':currency_id},
        }

        if not journal_id:
            return default
        
        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        account_id = False
        if journal.type in ('sale','sale_refund'):
            account_id = partner.property_account_receivable.id
        elif journal.type in ('purchase', 'purchase_refund','expense'):
            account_id = partner.property_account_payable.id
        else:
            account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id

        default['value']['account_id'] = account_id
        
        return default
    
    def onchange_paymode_line(self, cr, uid, ids, payment_lines, context=None):
        pay_mod_line_pool = self.pool.get('payment.mode.receipt.line')
        res={'value':{'amount':0.0}}
        #amount = 0.0        
        lines= [(x[1] , x[2]['amount']) for x in payment_lines]
        print payment_lines
        print lines

#        for line in lines:
#            pay_mod_line_pool.write(cr, uid, line[0], {'amount':line[1]})
            #amount += line[1] 
            #pay_line = pay_mod_line_pool.browse(cr, uid, line[0], context)
#        self.write(cr, uid, ids, {'amount':amount})
#        res['value']['amount'] = amount
        return res

    def get_invoices_and_credits(self, cr, uid, ids, context):

        if context is None:
            context = {}        
        line_pool = self.pool.get('account.voucher.line')
        currency_pool = self.pool.get('res.currency')
        move_line_pool = self.pool.get('account.move.line')
        ttype = context.get('type', 'receipt')
        line_cr_ids = []
        line_dr_ids = []
        lines = {}
        for v in self.browse(cr, uid, ids):
            lines = self._get_voucher_lines(cr, uid, v.id, context=context)
            if ttype == 'payment' and len(lines['line_cr_ids']) > 0:
                pre_line = 1
            elif ttype == 'receipt' and len(lines['line_dr_ids']) > 0:
                pre_line = 1
            else:
                pre_line = False
            self.write(cr, uid, v.id, {'pre_line':pre_line })
            #self._compute_voucher(cr, uid, v.id, voucher_line_ids, ttype, context=context_multi_currency)
        
        return True
        
    def _get_voucher_lines(self, cr, uid, ids, state='not_included', context=None):
        
        if context is None:
            context = {}        
        line_pool = self.pool.get('account.voucher.line')
        currency_pool = self.pool.get('res.currency')
        move_line_pool = self.pool.get('account.move.line')
        ttype = context.get('type', 'receipt')
        v = self.browse(cr, uid, ids)
        line_cr_ids = []
        line_dr_ids = []
        line_ids = []
        res={}
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
            if 'invoice_id' in context:
                domain += ['|', ('invoice','=',context['invoice_id']), ('debit','!=',0.0)]
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
                'state' : state,
            }
            
            # Creamos las lineas del voucher
            id = line_pool.create(cr, uid, rs)
            voucher_line_ids.append(id)
            rs['id'] = id
            if rs['type'] == 'cr':
                line_cr_ids.append(rs)
            elif rs['type'] == 'dr':
                line_dr_ids.append(rs)
            
        #payment_mode_lines = self._get_payment_lines_default(cr, uid, ids, context=context)    
        #line_pool.unpost_voucher_lines(cr, uid, voucher_line_ids, context=context)
        res = { 'line_cr_ids' : line_cr_ids , 'line_dr_ids': line_dr_ids } #,'payment_line_ids' : payment_mode_lines  } 
        
        return res

    def _compute_voucher(self, cr, uid, voucher_id, voucher_line_ids, ttype, context):

        if not voucher_line_ids:
            return False
                    
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
            line = move_line_obj.browse(cr, uid, vline.move_line_id.id)

            if line.credit:
                total_credit += vline.amount_unreconciled or 0.0
            else:
                total_debit += vline.amount_unreconciled or 0.0

        line_cr_ids = []
        line_dr_ids = []
      
        for vline in vline_obj.browse(cr, uid, voucher_line_ids):
            rs = {}
            line = move_line_obj.browse(cr, uid, vline.move_line_id.id)
            company_currency = v.journal_id.company_id.currency_id.id
            currency_id = v.currency_id.id
            if company_currency != currency_id and ttype == 'payment':
                total_debit = currency_pool.compute(cr, uid, currency_id, company_currency, total_debit, context=context)
            elif company_currency != currency_id and ttype == 'receipt':
                total_credit = currency_pool.compute(cr, uid, currency_id, company_currency, total_credit, context=context)

            if line.credit:
                amount = min(vline.amount_unreconciled, currency_pool.compute(cr, uid, company_currency, currency_id, abs(total_debit), context=context))
                rs['amount'] = amount
                total_debit -= amount
            else:
                amount = min(vline.amount_unreconciled, currency_pool.compute(cr, uid, company_currency, currency_id, abs(total_credit), context=context))
                rs['amount'] = amount
                total_credit -= amount

            vline_obj.write(cr, uid, vline.id, rs)

            if vline.type == 'cr':
                line_cr_ids.append(rs)
            else:
                line_dr_ids.append(rs)
            if ttype == 'payment' and len(line_cr_ids) > 0:
                pre_line = 1
            elif ttype == 'receipt' and len(line_dr_ids) > 0:
                pre_line = 1
        writeoff_amount = self._compute_writeoff_amount(cr, uid, line_dr_ids, line_cr_ids, price)
        self.write(cr, uid, v.id, {'pre_line':pre_line, 'writeoff_amount': writeoff_amount})

        return True
    
    def onchange_amount(self, cr, uid, ids, amount, context):
        print '**onchage_amount:' , amount 
        #self.write(cr, uid, ids, {'amount':amount})
#        return {'value': {'amount': amount}}
        return {}

    def onchange_line_ids(self, cr, uid, ids, line_dr_ids, line_cr_ids, amount):
        return {'value':{}}

    def onchange_journal_id(self, cr, uid, ids, context=None):
        return {'value':{}}
        
    def compute(self, cr, uid, ids, context=None):
        
        line_pool = self.pool.get('account.voucher.line')
        ttype = context.get('type', 'receipt')

        if context is None:
            context = {}
            
        for v in self.browse(cr, uid, ids):
            context_multi_currency = context.copy()
            if v.date:
                context_multi_currency.update({'date': v.date})            

        for v_id in ids: 
            voucher_line_ids = line_pool.search( cr, uid , [('voucher_id' ,'=', v_id ) , ( 'state' , '=', 'included')] )
            lines_no_amount  = line_pool.search( cr, uid , [('voucher_id' ,'=', v_id ) , 
                                                            ( 'state' , '=', 'not_included'),( 'amount' , '>', 0)])
    
        if len(lines_no_amount):
            line_pool.write(cr, uid , lines_no_amount , {'amount' : 0.0} ,context=None)
        if len(voucher_line_ids):
            self._compute_voucher(cr, uid, v.id, voucher_line_ids, ttype, context=context_multi_currency)
            
        return True

    
    def clean(self, cr, uid, ids, context=None):
        
        line_pool = self.pool.get('account.voucher.line')
        for v_id in ids: 
            lines_to_clean  = line_pool.search( cr, uid , [('voucher_id' ,'=', v_id ) ,'|', ( 'state' , '=', 'not_included')
                                                            ,'&',( 'state' , '=', 'included'),( 'amount' , '=', 0.0)])
        if lines_to_clean:
                line_pool.unlink(cr, uid, lines_to_clean)
        return True
       
    def proforma_voucher(self, cr, uid, ids, context=None):
        
        line_pool = self.pool.get('account.voucher.line')
        lines_to_post = []
        if not context:
            context = {}
        for voucher_id in ids:
            ttype = self.browse(cr, uid, voucher_id).type    
            context.update({'type':ttype})
            self.compute(cr, uid, ids, context)
            self.clean(cr, uid, ids, context)
            lines_to_post = line_pool.search(cr , uid , [('voucher_id' , '=' , voucher_id) , ('state' , '=' ,'included')] )
            line_pool.post_voucher_lines(cr, uid, lines_to_post, context=context)
            #self.action_move_line_create(cr, uid, ids, context=context)
                               
        return True
    
    def create(self, cr, uid, vals, context=None):
        res = self._get_payment_lines_default(cr, uid, context)
        payment_lines = [(0, 0, values) for values in res]        
        vals['payment_line_ids'] = payment_lines

        return super(account_voucher, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        print '**Write'
        print 'Vals:' , vals
        return super(account_voucher, self).write(cr, uid, ids, vals, context=context)

account_voucher()

class account_voucher_line(osv.osv):
    _name = 'account.voucher.line'
    _inherit = 'account.voucher.line'
    _columns = {
        'state' : fields.selection([('included','Included') , ('not_included','Not included') , ('posted','Posted')], readonly=True, string='State'),
    }
    _defaults = {
        'state': 'not_included',
    }

    def delete_voucher_line(self, cr, uid, ids, context=None):
        
        if not ids:
            return False
        for line in self.browse(cr, uid, ids):
            self.write(cr, uid , [line.id] , {'state' : 'not_included'} ,context=None)

        return True
    
    def add_voucher_line(self, cr, uid, ids, context=None):
        
        if not ids:
            return False
        for line in self.browse(cr, uid, ids):
            self.write(cr, uid , [line.id] , {'state' : 'included'} ,context=None)
            
        return True
        
    def post_voucher_lines(self, cr, uid, ids, context=None):

        if not ids:
            return False
        for line in self.browse(cr, uid, ids):
            self.write(cr, uid , [line.id] , {'state' : 'posted'} ,context=None)
            
        return True
    
    def unpost_voucher_lines(self, cr, uid, ids, context=None):

        if not ids:
            return False
        for line in self.browse(cr, uid, ids):
            self.write(cr, uid , [line.id] , {'state' : 'not_included'} ,context=None)
            
        return True
        
account_voucher_line()
