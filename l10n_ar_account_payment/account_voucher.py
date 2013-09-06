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
from tools.translate import _
import decimal_precision as dp

class account_voucher(osv.osv):

    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}

        for v in self.browse(cr, uid , ids, context):
            res[v.id] = {
                'total_invoices': 0.0,
                'total_credits': 0.0,
                'credit_balance': 0.0,
            }

            amount_credit = 0.0
            amount_debit = 0.0
            for line in v.line_dr_ids:
                if line.state == 'not_included' or not line.amount:
                    continue
                amount_credit += line.amount


            for line in v.line_cr_ids:
                if line.state == 'not_included' or not line.amount:
                    continue
                amount_debit += line.amount

            if v.type == 'payment':
                res[v.id]['total_credits'] = amount_debit
                res[v.id]['total_invoices'] = amount_credit
            else:
                res[v.id]['total_credits'] = amount_credit
                res[v.id]['total_invoices'] = amount_debit

            res[v.id]['credit_balance'] = v.amount - res[v.id]['total_invoices'] + res[v.id]['total_credits']

        return res


    def _total_amount(self, cr, uid, ids, name, arg, context=None):

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
      'total_invoices': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), type='float',  string='Total Invoices', multi='all'),
      'total_credits': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), type='float',  string='Total Credits', multi='all'),
      'credit_balance': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Account'), type='float',  string='Credit Balance', multi='all'),
    }

    def _get_payment_lines_default(self, cr, uid, context=None):

        pay_mod_pool = self.pool.get('payment.mode.receipt')
        modes = pay_mod_pool.search(cr, uid, [])
        if not modes:
            #TODO esto va en un log:
            print 'Warning - No se configuraron modos de pago (Payment Modes Receipt)'
        lines = []
        for mode in pay_mod_pool.browse(cr, uid, modes, context=context):
            lines.append({'name': mode.name ,'amount': 0.0 ,'amount_currency':0.0 ,'payment_mode_id': mode.id})

        return lines

    _defaults = {
        'pre_line': lambda *a: False,
    }

    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, company_id, context=None):
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
        default = {
                'value':{'line_ids':[], 'line_dr_ids':[], 'line_cr_ids':[], 'pre_line': False, 'currency_id': 1},
        }

        if not journal_id:
            return default

        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        
        if journal.currency:
            currency_id = journal.currency.id
        else:
            currency_id = journal.company_id.currency_id.id
        
        default['value']['currency_id'] = currency_id
        
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

        #pay_mod_line_pool = self.pool.get('payment.mode.receipt.line')
        res={'value':{'amount':0.0}}
        amount = 0.0
        #if context is None:
        #    context = {}
        lines= [(x[1] , x[2]['amount']) for x in payment_lines]
#
        for line in lines:
#            pay_mod_line_pool.write(cr, uid, line[0], {'amount':line[1]})
            amount += line[1]
#
        res['value']['amount'] = amount
        return res

    def get_invoices_and_credits(self, cr, uid, ids, context):

        if context is None:
            context = {}
        ttype = context.get('type', 'receipt')
        state = 'not_included'
        if context.get('included', False):
            state = 'included'
        lines = {}
        for v in self.browse(cr, uid, ids):
            lines = self._get_voucher_lines(cr, uid, v.id, state=state, context=context)
            if ttype == 'payment' and len(lines['line_cr_ids']) > 0:
                pre_line = 1
            elif ttype == 'receipt' and len(lines['line_dr_ids']) > 0:
                pre_line = 1
            else:
                pre_line = False
            self.write(cr, uid, v.id, {'pre_line':pre_line })

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

            invoice_ids = []
            if 'invoice_id' in context:
                invoice_ids.append(context['invoice_id'])

            if 'invoice_ids' in context:
                invoice_ids += context['invoice_ids']

            if invoice_ids:
                if ttype == 'payment':
                    domain += ['|', ('invoice','in',invoice_ids), ('debit','!=',0.0)]
                else:
                    domain += ['|', ('invoice','in',invoice_ids), ('credit','!=',0.0)]
            ids = move_line_pool.search(cr, uid, domain, context=context)
        else:
            ids = context['move_line_ids']
        ids.reverse()
        moves = move_line_pool.browse(cr, uid, ids, context=context)
        company_currency = v.journal_id.company_id.currency_id.id
        currency_id = v.currency_id.id
        voucher_line_ids = []
        for line in moves:
            # Se comenta esta parte, sino no aparecen los creditos parcialmente conciliados
            #if line.credit and line.reconcile_partial_id and ttype == 'receipt':
            #    continue

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

        #solo para realizar pruebas:
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

    def onchange_line_ids(self, cr, uid, ids, line_dr_ids, line_cr_ids, amount):

        included_dr = [l[2] for l in line_dr_ids if l[2]['state'] == 'included']
        included_cr = [l[2] for l in line_cr_ids if l[2]['state'] == 'included']

        total_debits = 0.0
        total_credits = 0.0
        for line in included_dr:
            print line['amount_unreconciled'], line['amount']
            total_debits += line['amount']

        for line in included_cr:
            print line['amount_unreconciled'], line['amount']
            total_credits += line['amount']

        print 'Total Debits: ', total_debits
        print 'Total Credits: ', total_credits

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
        pay_mode_line_pool = self.pool.get('payment.mode.receipt.line')

        for v_id in ids:
            vlines_to_clean  = line_pool.search( cr, uid , [('voucher_id' ,'=', v_id ) ,'|', ( 'state' , '=', 'not_included')
                                                            ,'&',( 'state' , '=', 'included'),( 'amount' , '=', 0.0)])
            pay_modes_to_clean = pay_mode_line_pool.search(cr, uid , [('voucher_id' ,'=', v_id ) , ( 'amount' , '=', 0.0)])

        if vlines_to_clean:
            line_pool.unlink(cr, uid, vlines_to_clean)
        if pay_modes_to_clean:
            pay_mode_line_pool.unlink(cr, uid, pay_modes_to_clean)

        return True

    def proforma_voucher(self, cr, uid, ids, context=None):

        line_pool = self.pool.get('account.voucher.line')
        lines_to_post = []
        if not context:
            context = {}
        for voucher in self.browse(cr, uid, ids, context):
            ttype = self.browse(cr, uid, voucher.id).type
            context.update({'type':ttype})
            #self.compute(cr, uid, ids, context)

            # Chequeamos si estamos usando mas dinero del que tenemos
            if voucher.credit_balance < 0.0:
                raise osv.except_osv(_('Error'), _('Credit balance of the voucher cannot negative'))

            self.clean(cr, uid, ids, context)
            lines_to_post = line_pool.search(cr , uid , [('voucher_id' , '=' , voucher.id) , ('state' , '=' ,'included')] )
            line_pool.post_voucher_lines(cr, uid, lines_to_post, context=context)
            self.action_move_line_create(cr, uid, [voucher.id], context=context)

        return True

    # Hook method to override in others modules if need to add more
    # account.move.line to be included in the account.move generated by the voucher
    def create_move_line_hook(self, cr, uid, voucher_id, move_id, move_lines, context={}):
        return move_lines

    def action_move_line_create(self, cr, uid, ids, context=None):

        def _get_payment_term_lines(term_id, amount):
            term_pool = self.pool.get('account.payment.term')
            if term_id and amount:
                terms = term_pool.compute(cr, uid, term_id, amount)
                return terms
            return False
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        currency_pool = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        seq_obj = self.pool.get('ir.sequence')
        for inv in self.browse(cr, uid, ids, context=context):
            if inv.move_id:
                continue
            context_multi_currency = context.copy()
            context_multi_currency.update({'date': inv.date})

            if inv.number:
                name = inv.number
            elif inv.journal_id.sequence_id:
                name = seq_obj.get_id(cr, uid, inv.journal_id.sequence_id.id)
            else:
                raise osv.except_osv(_('Error !'), _('Please define a sequence on the journal !'))
            if not inv.reference:
                ref = name.replace('/','')
            else:
                ref = inv.reference

            move = {
                'name': name,
                'journal_id': inv.journal_id.id,
                'narration': inv.narration,
                'date': inv.date,
                'ref': ref,
                'period_id': inv.period_id and inv.period_id.id or False
            }
            move_id = move_pool.create(cr, uid, move)

            # Creamos las lineas correspondientes a formas de pago
            # TODO: Calcular la amount_currency para los payment_mode_line
            # TODO: Probar para los demas tipos de este objeto: Supplier Payment, Sale&Purchase Receipt
            total_debit = 0
            total_credit = 0

            company_currency = inv.journal_id.company_id.currency_id.id

            pml = []
            for payment_line in inv.payment_line_ids:
                #print 'Metodo de pago: ', payment_line.name, payment_line.amount, payment_line.payment_mode_id.account_id.name
                if payment_line.amount == 0.0:
                    continue

                # TODO: Chequear que funcione bien en multicurrency
                current_currency = payment_line.currency.id

                debit = 0.0
                credit = 0.0
                # TODO: is there any other alternative then the voucher type ??
                # -for sale, purchase we have but for the payment and receipt we do not have as based on the bank/cash journal we can not know its payment or receipt
                if inv.type in ('purchase', 'payment'):
                    credit = currency_pool.compute(cr, uid, current_currency, company_currency, payment_line.amount, context=context_multi_currency)
                elif inv.type in ('sale', 'receipt'):
                    debit = currency_pool.compute(cr, uid, current_currency, company_currency, payment_line.amount, context=context_multi_currency)
                if debit < 0:
                    credit = -debit
                    debit = 0.0
                if credit < 0:
                    debit = -credit
                    credit = 0.0
                sign = debit - credit < 0 and -1 or 1

                # Creamos la linea contable perteneciente a las formas de pago
                move_line = {
                    'name': inv.name or '/',
                    'debit': debit,
                    'credit': credit,
                    'account_id': payment_line.payment_mode_id.account_id.id,
                    'move_id': move_id,
                    'journal_id': inv.journal_id.id,
                    'period_id': inv.period_id.id,
                    'partner_id': inv.partner_id.id,
                    'currency_id': company_currency <> current_currency and  current_currency or False,
                    'amount_currency': company_currency <> current_currency and sign * payment_line.amount or 0.0,
                    'date': inv.date,
                    'date_maturity': inv.date_due
                }

                # TODO: Se podrian hacer los move_lines como una lista de diccionarios para luego
                # crear el account.move y agregarle los account.move.line de todos los modulos que
                # puedan agregar. Ver codigo en invoice.py en action_move_create
                pml.append(move_line)

            # Metodo de hook para poder agregar account_move_lines de otros modulos
            # Por ejemplo, l10n_ar_account_check o l10n_ar_retentions_basic
            pml = self.create_move_line_hook(cr, uid, inv.id, move_id, pml, context=context)

            #print 'PML: ', pml
            for ml in pml:
                total_debit += ml['debit']
                total_credit += ml['credit']
                move_line_pool.create(cr, uid, ml)

            rec_list_ids = []
            line_total = total_debit - total_credit

            # TODO: Tener en cuenta que esta funcion tiene que servir
            # para customer_payment, supplier_payment, sales_receipt y purchase_receipt
            if inv.type == 'sale':
                line_total = line_total - currency_pool.compute(cr, uid, inv.currency_id.id, company_currency, inv.tax_amount, context=context_multi_currency)
            elif inv.type == 'purchase':
                line_total = line_total + currency_pool.compute(cr, uid, inv.currency_id.id, company_currency, inv.tax_amount, context=context_multi_currency)

            for line in inv.line_ids:
                #create one move line per voucher line where amount is not 0.0
                if not line.amount:
                    continue
                #we check if the voucher line is fully paid or not and create a move line to balance the payment and initial invoice if needed
                if line.amount == line.amount_unreconciled:
                    amount = line.move_line_id.amount_residual #residual amount in company currency
                else:
                    amount = currency_pool.compute(cr, uid, inv.currency_id.id, company_currency, line.untax_amount or line.amount, context=context_multi_currency)
                move_line = {
                    'journal_id': inv.journal_id.id,
                    'period_id': inv.period_id.id,
                    'name': line.name and line.name or '/',
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'partner_id': inv.partner_id.id,
                    'currency_id': company_currency <> inv.currency_id.id and inv.currency_id.id or False,
                    'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                    'quantity': 1,
                    'credit': 0.0,
                    'debit': 0.0,
                    'date': inv.date
                }
                if amount < 0:
                    amount = -amount
                    if line.type == 'dr':
                        line.type = 'cr'
                    else:
                        line.type = 'dr'

                if (line.type=='dr'):
                    line_total += amount
                    move_line['debit'] = amount
                else:
                    line_total -= amount
                    move_line['credit'] = amount

                if inv.tax_id and inv.type in ('sale', 'purchase'):
                    move_line.update({
                        'account_tax_id': inv.tax_id.id,
                    })
                if move_line.get('account_tax_id', False):
                    tax_data = tax_obj.browse(cr, uid, [move_line['account_tax_id']], context=context)[0]
                    if not (tax_data.base_code_id and tax_data.tax_code_id):
                        raise osv.except_osv(_('No Account Base Code and Account Tax Code!'),_("You have to configure account base code and account tax code on the '%s' tax!") % (tax_data.name))
                sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
                move_line['amount_currency'] = company_currency <> inv.currency_id.id and sign * line.amount or 0.0
                voucher_line = move_line_pool.create(cr, uid, move_line)
                if line.move_line_id.id:
                    rec_ids = [voucher_line, line.move_line_id.id]
                    rec_list_ids.append(rec_ids)

            # TODO: Que pasa si el voucher_currency y las currency de los
            # metodos de pago son diferentes?
            inv_currency_id = inv.currency_id or inv.journal_id.currency or inv.journal_id.company_id.currency_id
            if not currency_pool.is_zero(cr, uid, inv_currency_id, line_total):
                diff = line_total
                current_currency = inv_currency_id.id

                account_id = False
                with_writeoff = False

                # TODO: BAD HACK: Todavia no hicimos la configuracion de la cuenta de Writeoff
                # por lo tanto, lo forzamos. Sacar esto urgente
                if abs(round(diff, 2)) <= 1:
                    with_writeoff = True
                #if inv.payment_option == 'with_writeoff':
                if with_writeoff:
                    #account_id = inv.writeoff_acc_id.id
                    account_id = self.pool.get('account.account').search(cr, uid, [('name', 'ilike', 'Diferencia')])[0]
                    if not account_id:
                        osv.except_osv(_('Cuenta de Writeoff'), _('Not writeoff account configured'))
                elif inv.type in ('sale', 'receipt'):
                    account_id = inv.partner_id.property_account_receivable.id
                else:
                    account_id = inv.partner_id.property_account_payable.id
                move_line = {
                    'name': name,
                    'account_id': account_id,
                    'move_id': move_id,
                    'partner_id': inv.partner_id.id,
                    'date': inv.date,
                    'credit': diff > 0 and diff or 0.0,
                    'debit': diff < 0 and -diff or 0.0,
                    'amount_currency': company_currency <> current_currency and currency_pool.compute(cr, uid, company_currency, current_currency, diff * -1, context=context_multi_currency) or 0.0,
                    'currency_id': company_currency <> current_currency and current_currency or False,
                }
                move_line_pool.create(cr, uid, move_line)
            self.write(cr, uid, [inv.id], {
                'move_id': move_id,
                'state': 'posted', #TODO: Quitar este state=posted ya que el move_pool.post de mas abajo ya lo pasa a ese estado.
                'number': name,
            })
            move_pool.post(cr, uid, [move_id], context={})
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    move_line_pool.reconcile_partial(cr, uid, rec_ids)

        return True

    def create(self, cr, uid, vals, context=None):
        # Si no hay ninguna payment_line para crear, creamos las por defecto
        # Esto sirve para cuando creamos un voucher desde codigo que no necesitamos
        # las payment_lines por defecto, asi que tenemos que incluir
        # las que querramos en vals
        if 'payment_line_ids' not in vals or vals['payment_line_ids'] == []:
            res = self._get_payment_lines_default(cr, uid, context)
            payment_lines = [(0, 0, values) for values in res]
            vals['payment_line_ids'] = payment_lines

        return super(account_voucher, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):

        if not context:
            context = {}
        #if 'payment_line_ids' in vals:
        #    del vals['payment_line_ids']

        return super(account_voucher, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, vals, context=None):

        if not context:
            context = {}

        payment_mode_line_obj = self.pool.get('payment.mode.receipt.line')

        for voucher in self.browse(cr, uid, ids):
            for payment_line in voucher.payment_line_ids:
                payment_mode_line_obj.unlink(cr, uid, payment_line.id, context)

        return super(account_voucher, self).unlink(cr, uid, ids, context=context)

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
