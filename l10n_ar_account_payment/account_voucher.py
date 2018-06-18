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

from osv import osv, fields
from tools.translate import _
from openerp.addons.account_voucher.account_voucher import account_voucher as account_voucher_orig

class account_voucher(osv.osv):

    _name = "account.voucher"
    _inherit = "account.voucher"

    def _get_journal(self, cr, uid, context=None):
        res = super(account_voucher, self)._get_journal(cr, uid, context)
        ttype = context.get('type', 'bank')
        if ttype in ('payment', 'receipt'):
            res = self._make_journal_search(cr, uid, ttype, context=context)
            res = res[0] or False

        return res

    _columns = {
      'payment_line_ids': fields.one2many('payment.mode.receipt.line' , 'voucher_id' , 'Payments Lines'),
      'account_id':fields.many2one('account.account', 'Account', required=False, readonly=True, states={'draft':[('readonly',False)]}),
    }

    _defaults = {
        'journal_id':_get_journal,
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if context is None: context = {}
        return [(r['id'], (str("%s - %.2f" % (r['reference'], r['amount'])) or '')) for r in self.read(cr, uid, ids, ['reference', 'amount'], context, load='_classic_write')]

    def _get_payment_lines_amount(self, cr, uid, payment_line_ids, context=None):
        payment_line_obj = self.pool.get('payment.mode.receipt.line')
        amount = 0.0

        for payment_line in payment_line_ids:
            # Si tiene id, y no tiene amount, leemos el amount
            if payment_line[1] and not payment_line[2]:
                am = payment_line_obj.read(cr, uid, payment_line[1], ['amount'], context=context)['amount']
                if am:
                    amount += float(am)
            elif payment_line[2]:
                amount += payment_line[2]['amount']

        return amount

    def onchange_payment_line(self, cr, uid, ids, amount, payment_line_ids, context=None):

        amount = self._get_payment_lines_amount(cr, uid, payment_line_ids, context)
        return {'value': {'amount': amount}}

    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
        res = super(account_voucher, self).onchange_partner_id(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=context)

        if not partner_id:
            res['value']['payment_line_ids'] = []
            return res

        if not 'value' in res:
            return res

        res2 = self._get_payment_lines_default(cr, uid, ttype, currency_id, context=context)
        res['value']['payment_line_ids'] = res2

        return res

    def _get_payment_lines_default(self, cr, uid, ttype, currency_id, context=None):

        pay_method_obj = self.pool.get('account.journal')
        methods = pay_method_obj.search(cr, uid, [('type', 'in', ['cash', 'bank']), '|', ('currency','=',currency_id), ('currency','=',False)])
        if not methods:
            return {}

        lines = []
        for method in pay_method_obj.browse(cr, uid, methods, context=context):
            lines.append({'name': method.name ,'amount': 0.0 ,'amount_currency':0.0 ,'payment_mode_id': method.id, 'currency': method.currency.id})

        return lines

    def _clean_payment_lines(self, cr, uid, ids, context=None):

        lines_to_unlink = []

        for voucher in self.browse(cr, uid, ids, context=context):
            for payment_line in voucher.payment_line_ids:
                if payment_line.amount == 0:
                    lines_to_unlink.append(payment_line.id)

        self.pool.get('payment.mode.receipt.line').unlink(cr, uid, lines_to_unlink, context=context)
        return True

    def proforma_voucher(self, cr, uid, ids, context=None):
        if not context:
            context = {}

        # Chequeamos si la writeoff_amount no es negativa
        writeoff_amount = self.read(cr, uid, ids, ['writeoff_amount'], context=context)[0]['writeoff_amount']

        if round(writeoff_amount, 2) < 0.0:
            raise osv.except_osv(_("Validate Error!"), _("Cannot validate a voucher with negative amount. Please check that Writeoff Amount is not negative."))

        self._clean_payment_lines(cr, uid, ids, context=context)

        self.action_move_line_create(cr, uid, ids, context=context)

        return True

    def create_move_line_hook(self, cr, uid, voucher_id, move_id, move_lines, context={}):
        return move_lines

    def _convert_paid_amount_in_company_currency(self, cr, uid, voucher, amount, context=None):
        if context is None:
            context = {}
        res = {}
        ctx = context.copy()
        ctx.update({'date': voucher.date})
        #make a new call to browse in order to have the right date in the context, to get the right currency rate
        voucher = self.browse(cr, uid, voucher.id, context=ctx)
        ctx.update({
          'voucher_special_currency': voucher.payment_rate_currency_id and voucher.payment_rate_currency_id.id or False,
          'voucher_special_currency_rate': voucher.currency_id.rate * voucher.payment_rate,})
        res = self.pool.get('res.currency').compute(cr, uid, voucher.currency_id.id, voucher.company_id.currency_id.id, amount, context=ctx)
        return res

    # Heredada para agregar un hook y los asientos para varias formas de pago
    def create_move_lines(self, cr, uid, voucher_id, move_id, company_currency, current_currency, context=None):
        '''
        Return a dict to be use to create account move lines of given voucher.

        :param voucher_id: Id of voucher what we are creating account_move.
        :param move_id: Id of account move where this line will be added.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: mapping between fieldname and value of account move line to create
        :rtype: dict
        '''
        voucher = self.pool.get('account.voucher').browse(cr,uid,voucher_id,context)
        total_debit = total_credit = 0.0
        # TODO: is there any other alternative then the voucher type ??
        # ANSWER: We can have payment and receipt "In Advance".
        # TODO: Make this logic available.
        # -for sale, purchase we have but for the payment and receipt we do not have as based on the bank/cash journal we can not know its payment or receipt
        if voucher.type in ('purchase', 'payment'):
            total_credit = voucher.paid_amount_in_company_currency
        elif voucher.type in ('sale', 'receipt'):
            total_debit = voucher.paid_amount_in_company_currency
        if total_debit < 0: total_credit = -total_debit; total_debit = 0.0
        if total_credit < 0: total_debit = -total_credit; total_credit = 0.0
        sign = total_debit - total_credit < 0 and -1 or 1

        # Creamos una move_line por payment_line
        move_lines = []
        for pl in voucher.payment_line_ids:
            if pl.amount == 0.0:
                continue

            amount_in_company_currency =  self._convert_paid_amount_in_company_currency(cr, uid, voucher, pl.amount, context=context)
            #self.pool.get('res.currency').compute(cr, uid, pl.currency.id, voucher.company_id.currency_id.id, pl.amount, context=context)

            debit = credit = 0.0
            if voucher.type in ('purchase', 'payment'):
                credit = amount_in_company_currency
                pl_account_id = pl.payment_mode_id.default_credit_account_id.id
            elif voucher.type in ('sale', 'receipt'):
                debit = amount_in_company_currency
                pl_account_id = pl.payment_mode_id.default_debit_account_id.id
            if debit < 0: credit = -debit; debit = 0.0
            if credit < 0: debit = -credit; credit = 0.0
            sign = debit - credit < 0 and -1 or 1

            move_line = {
                    'name': pl.name or '/',
                    'debit': debit,
                    'credit': credit,
                    'account_id': pl_account_id,
                    'move_id': move_id,
                    'journal_id': voucher.journal_id.id,
                    'period_id': voucher.period_id.id,
                    'partner_id': voucher.partner_id.id,
                    'currency_id': company_currency <> current_currency and  current_currency or False,
                    'amount_currency': company_currency <> current_currency and sign * pl.amount or 0.0,
                    'date': voucher.date,
                    'date_maturity': voucher.date_due
            }

            move_lines.append(move_line)

        # Creamos un hook para agregar los demas asientos contables de otros modulos
        self.create_move_line_hook(cr, uid, voucher.id, move_id, move_lines, context=context)

        # Recorremos las lineas para  hacer un chequeo de debit y credit contra total_debit y total_credit
        amount_credit = 0.0
        amount_debit = 0.0
        for line in move_lines:
            amount_credit += line['credit']
            amount_debit += line['debit']

        if round(amount_credit, 3) != round(total_credit, 3) or round(amount_debit, 3) != round(total_debit, 3):
            if voucher.type in ('purchase', 'payment'):
                amount_credit -= amount_debit
                amount_debit -= amount_debit
            else:
                amount_debit -= amount_credit
                amount_credit -= amount_credit

            if round(amount_credit, 3) != round(total_credit, 3) or round(amount_debit, 3) != round(total_debit, 3):
                raise osv.except_osv(_('Voucher Error!'), _('Voucher Paid Amount and sum of different payment mode must be equal'))

        return move_lines

    def _update_move_reference(self, cr, uid, move_id, ref, context=None):

        cr.execute('UPDATE account_move SET ref=%s ' \
                'WHERE id=%s', (ref, move_id))

        cr.execute('UPDATE account_move_line SET ref=%s ' \
                'WHERE move_id=%s', (ref, move_id))

        cr.execute('UPDATE account_analytic_line SET ref=%s ' \
                'FROM account_move_line ' \
                'WHERE account_move_line.move_id = %s ' \
                    'AND account_analytic_line.move_id = account_move_line.id',
                    (ref, move_id))
        return True

    def action_move_line_create(self, cr, uid, ids, context=None):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        for voucher in self.browse(cr, uid, ids, context=context):
            if voucher.move_id:
                continue
            company_currency = self._get_company_currency(cr, uid, voucher.id, context)
            current_currency = self._get_current_currency(cr, uid, voucher.id, context)
            # we select the context to use accordingly if it's a multicurrency case or not
            context = self._sel_context(cr, uid, voucher.id, context)
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = context.copy()
            ctx.update({'date': voucher.date})
            # Create the account move record.
            move_id = move_pool.create(cr, uid, self.account_move_get(cr, uid, voucher.id, context=context), context=context)
            # Get the name of the account_move just created
            name = move_pool.browse(cr, uid, move_id, context=context).name

            if voucher.type in ('payment', 'receipt'):
                # Creamos las lineas contables de todas las formas de pago, etc
                move_line_vals = self.create_move_lines(cr,uid,voucher.id, move_id, company_currency, current_currency, context)
                line_total = 0.0
                for vals in move_line_vals:
                    line_total += vals['debit'] - vals['credit']
                    move_line_pool.create(cr, uid, vals, context)
            else:  #('sale', 'purchase')
                # Create the first line of the voucher
                move_line_id = move_line_pool.create(cr, uid, self.first_move_line_get(cr,uid,voucher.id, move_id, company_currency, current_currency, context), context)
                move_line_brw = move_line_pool.browse(cr, uid, move_line_id, context=context)
                line_total = move_line_brw.debit - move_line_brw.credit

            #move_line_brw = move_line_pool.browse(cr, uid, move_line_id, context=context)
            #line_total = move_line_brw.debit - move_line_brw.credit
            rec_list_ids = []
            if voucher.type == 'sale':
                line_total = line_total - self._convert_amount(cr, uid, voucher.tax_amount, voucher.id, context=ctx)
            elif voucher.type == 'purchase':
                line_total = line_total + self._convert_amount(cr, uid, voucher.tax_amount, voucher.id, context=ctx)
            # Create one move line per voucher line where amount is not 0.0
            line_total, rec_list_ids = self.voucher_move_line_create(cr, uid, voucher.id, line_total, move_id, company_currency, current_currency, context)

            # Create the writeoff line if needed
            ml_writeoff = self.writeoff_move_line_get(cr, uid, voucher.id, line_total, move_id, name, company_currency, current_currency, context)
            if ml_writeoff:
                move_line_pool.create(cr, uid, ml_writeoff, context)

            # We post the voucher.
            self.write(cr, uid, [voucher.id], {
                'move_id': move_id,
                'state': 'posted',
                'number': name,
            })
            if voucher.journal_id.entry_posted:
                move_pool.post(cr, uid, [move_id], context={})
            # We automatically reconcile the account move lines.
            reconcile = False
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    reconcile = move_line_pool.reconcile_partial(cr, uid, rec_ids, writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id)

            # Borramos las lineas que estan en 0
            lines_to_unlink = []
            for line in voucher.line_ids:
                if not line.amount:
                    lines_to_unlink.append(line.id)

            self.pool.get('account.voucher.line').unlink(cr, uid, lines_to_unlink, context=context)

        return True

#    def recompute_voucher_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
#
#        print 'recompute_voucher_lines: ', __name__
#
#        default = super(account_voucher, self).recompute_voucher_lines(cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=context)
#
#        ml_obj = self.pool.get('account.move.line')
#
#        for vals in default['value']['line_dr_ids']+default['value']['line_cr_ids']:
#            if vals['move_line_id']:
#                reads = ml_obj.read(cr, uid, vals['move_line_id'], ['invoice', 'ref'], context=context)
#                vals['invoice_id'] = reads['invoice'] and reads['invoice'][0] or False
#                vals['ref'] = reads['ref']
#        return default

    def _get_move_line_ids(self, cr, uid, voucher_ids, partner_id, account_type, context):
        move_line_obj = self.pool.get('account.move.line')

        if not context.get('move_line_ids', False):
            ids = move_line_obj.search(cr, uid, [('state','=','valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False), ('partner_id', '=', partner_id)], context=context)
        else:
            ids = context['move_line_ids']
        return ids


    def _get_move_lines_found(self, cr, uid, line, price, invoice_id,
            currency_id, company_currency, move_lines_found, context=None):

        to_break = False

        if invoice_id:
            if line.invoice.id == invoice_id:
                #if the invoice linked to the voucher line is equal to the invoice_id in context
                #then we assign the amount on that line, whatever the other voucher lines
                move_lines_found.append(line.id)
        elif currency_id == company_currency:
            #otherwise treatments is the same but with other field names
            if line.amount_residual == price:
                #if the amount residual is equal the amount voucher, we assign it to that voucher
                #line, whatever the other voucher lines
                move_lines_found.append(line.id)
                to_break = True
            #otherwise we will split the voucher amount on each line (by most old first)
        elif currency_id == line.currency_id.id:
            if line.amount_residual_currency == price:
                move_lines_found.append(line.id)
                to_break = True

        return to_break

    def _get_voucher_line_vals(self, line, line_currency_id,
            amount, amount_original, amount_unreconciled):

        rs = {
            'name':line.move_id.name,
            'type': line.credit and 'dr' or 'cr',
            'move_line_id':line.id,
            'account_id':line.account_id.id,
            'amount_original': amount_original,
            'amount': amount,
            'date_original':line.date,
            'date_due':line.date_maturity,
            'amount_unreconciled': amount_unreconciled,
            'currency_id': line_currency_id,
            'invoice_id': line.invoice.id,
            'ref': line.ref,
        }
        return rs

    def _try_autoimpute(self, rs, line, amount_unreconciled,
            total_debit, total_credit):
        if line.credit:
            amount = min(amount_unreconciled, abs(total_debit))
            rs['amount'] = amount
            total_debit -= amount
        else:
            amount = min(amount_unreconciled, abs(total_credit))
            rs['amount'] = amount
            total_credit -= amount

        return total_debit, total_credit

    # PATCHED Method
    def recompute_voucher_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
        """
        Returns a dict that contains new values and context

        @param partner_id: latest value from user input for field partner_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """
        def _remove_noise_in_o2m():
            """if the line is partially reconciled, then we must pay attention to display it only once and
                in the good o2m.
                This function returns True if the line is considered as noise and should not be displayed
            """
            if line.reconcile_partial_id:
                if currency_id == line.currency_id.id:
                    if line.amount_residual_currency <= 0:
                        return True
                else:
                    if line.amount_residual <= 0:
                        return True
            return False

        if context is None:
            context = {}
        context_multi_currency = context.copy()

        currency_pool = self.pool.get('res.currency')
        move_line_pool = self.pool.get('account.move.line')
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')
        line_pool = self.pool.get('account.voucher.line')

        #set default values
        default = {
            'value': {'line_dr_ids': [] ,'line_cr_ids': [] ,'pre_line': False,},
        }

        #drop existing lines
        line_ids = ids and line_pool.search(cr, uid, [('voucher_id', '=', ids[0])]) or False
        if line_ids:
            line_pool.unlink(cr, uid, line_ids)

        if not partner_id or not journal_id:
            return default

        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        currency_id = currency_id or journal.company_id.currency_id.id

        total_credit = 0.0
        total_debit = 0.0
        account_type = None
        if context.get('account_id'):
            account_type = self.pool['account.account'].browse(cr, uid, context['account_id'], context=context).type
        if ttype == 'payment':
            if not account_type:
                account_type = 'payable'
            total_debit = price or 0.0
        else:
            total_credit = price or 0.0
            if not account_type:
                account_type = 'receivable'

        ids = self._get_move_line_ids(cr, uid, ids, partner_id, account_type, context=context)

        invoice_id = context.get('invoice_id', False)
        company_currency = journal.company_id.currency_id.id
        move_lines_found = []

        #order the lines by most old first
        ids.reverse()
        account_move_lines = move_line_pool.browse(cr, uid, ids, context=context)

        # Differentiate lines by currency, so that, can be
        # automatically applied only amounts on same currency
        lines_same_currency = []
        lines_diff_currency = []

        #compute the total debit/credit and look for a matching open amount or invoice
        for line in account_move_lines:
            if _remove_noise_in_o2m():
                continue

            to_break = self._get_move_lines_found( cr, uid, line, price,
                            invoice_id, currency_id, company_currency,
                            move_lines_found, context=context)

            line_currency_id = line.currency_id and \
                    line.currency_id.id or company_currency

            if currency_id == line_currency_id:
                lines_same_currency.append(line)
            else:
                lines_diff_currency.append(line)

            if to_break:
                break

        if currency_id == company_currency:
            total_credit = sum(map(
                lambda x: x.credit or 0.0, lines_same_currency))
            total_debit = sum(map(
                lambda x: x.debit or 0.0, lines_same_currency))
        elif currency_id == line.currency_id.id:
            total_credit = sum(map(
                lambda x: x.credit and x.amount_currency or 0.0,
                lines_same_currency))
            total_debit = sum(map(
                lambda x: x.debit and x.amount_currency or 0.0,
                lines_same_currency))

        remaining_amount = price
        #voucher line creation
        for line in lines_same_currency+lines_diff_currency:

            if line.currency_id and currency_id == line.currency_id.id:
                amount_original = abs(line.amount_currency)
                amount_unreconciled = abs(line.amount_residual_currency)
            else:
                #always use the amount booked in the company currency as the basis of the conversion into the voucher currency
                amount_original = currency_pool.compute(cr, uid, company_currency, currency_id, line.credit or line.debit or 0.0, context=context_multi_currency)
                amount_unreconciled = currency_pool.compute(cr, uid, company_currency, currency_id, abs(line.amount_residual), context=context_multi_currency)
            line_currency_id = line.currency_id and line.currency_id.id or company_currency

            # Calculate amount to impute
            amount = (line.id in move_lines_found) and min(abs(remaining_amount), amount_unreconciled) or 0.0
            rs = self._get_voucher_line_vals(line, line_currency_id,
                    amount, amount_original, amount_unreconciled)

            remaining_amount -= rs['amount']

            #in case a corresponding move_line hasn't been found, we now try to assign the voucher amount
            #on existing invoices: we split voucher amount by most old first, but only for lines in the same currency
            disable_autoimpute = False
            if ttype == 'receipt':
                disable_autoimpute = self.pool['res.users'].has_group(
                            cr, uid, 'l10n_ar_account_payment.'
                            'group_disable_auto_impute_receipts')
            elif ttype == 'payment':
                disable_autoimpute = self.pool['res.users'].has_group(
                            cr, uid, 'l10n_ar_account_payment.'
                            'group_disable_auto_impute_payments')

            if not move_lines_found:
                if currency_id == line_currency_id:
                    if not disable_autoimpute:
                        # Auto reimpute
                        total_debit, total_credit = self._try_autoimpute(
                                rs, line, amount_unreconciled,
                                total_debit, total_credit)

            if rs['amount_unreconciled'] == rs['amount']:
                rs['reconcile'] = True

            if rs['type'] == 'cr':
                default['value']['line_cr_ids'].append(rs)
            else:
                default['value']['line_dr_ids'].append(rs)

        # NOTE: Indented down to avoid recomputation of writeoff in every loop
        if len(default['value']['line_cr_ids']) > 0:
            default['value']['pre_line'] = 1
        elif len(default['value']['line_dr_ids']) > 0:
            default['value']['pre_line'] = 1
        default['value']['writeoff_amount'] = self._compute_writeoff_amount(cr, uid, default['value']['line_dr_ids'], default['value']['line_cr_ids'], price, ttype)
        return default


account_voucher()

# NOTE: Patching recompute_voucher_lines to insert some hooks
origin = getattr(account_voucher_orig, 'recompute_voucher_lines')
setattr(account_voucher_orig, 'recompute_voucher_lines', account_voucher_orig.recompute_voucher_lines)

class account_voucher_line(osv.osv):
    _name = 'account.voucher.line'
    _inherit = 'account.voucher.line'


    _columns = {
        'invoice_id': fields.many2one('account.invoice', string='Invoice'),
        'ref': fields.char('Reference', size=64),
    }

    def onchange_amount(self, cr, uid, ids, amount, amount_unreconciled, context=None):
        vals = {}
        if amount:
            vals['reconcile'] = (round(amount, 2) == round(amount_unreconciled, 2))
        return {'value': vals}

account_voucher_line()
