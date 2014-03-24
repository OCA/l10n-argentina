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

class account_voucher(osv.osv):

    _name = "account.voucher"
    _inherit = "account.voucher"

    _columns = {
      'payment_line_ids': fields.one2many('payment.mode.receipt.line' , 'voucher_id' , 'Payments Lines'),
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if context is None: context = {}
        return [(r['id'], (str("%s - %.2f" % (r['number'], r['amount'])) or '')) for r in self.read(cr, uid, ids, ['number', 'amount'], context, load='_classic_write')]

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

        pay_mod_pool = self.pool.get('payment.mode.receipt')
        modes = pay_mod_pool.search(cr, uid, [('type', '=', ttype), ('currency','=',currency_id)])
        if not modes:
            return {}

        lines = []
        for mode in pay_mod_pool.browse(cr, uid, modes, context=context):
            lines.append({'name': mode.name ,'amount': 0.0 ,'amount_currency':0.0 ,'payment_mode_id': mode.id, 'currency': mode.currency.id})

        return lines

    def _clean_payment_lines(self, cr, uid, ids, context=None):

        lines_to_unlink = []

        for voucher in self.browse(cr, uid, ids, context=context):
            for payment_line in voucher.payment_line_ids:
                if payment_line.amount == 0:
                    lines_to_unlink.append(payment_line.id)

        self.pool.get('payment.mode.receipt.line').unlink(cr, uid, lines_to_unlink, context=context)
        return True

#    def _hook_get_amount(self, cr, uid, ids, amount, context=None):
#
#        lines_to_unlink = []
#
#        for voucher in self.browse(cr, uid, ids, context=context):
#            for payment_line in voucher.payment_line_ids:
#                if payment_line.amount == 0:
#                    lines_to_unlink.append(payment_line.id)
#
#                amount += payment_line.amount
#
#        if context.get('zero_check', False):
#            self.pool.get('payment.mode.receipt.line').unlink(cr, uid, lines_to_unlink, context=context)
#        return amount

    def proforma_voucher(self, cr, uid, ids, context=None):
        # Escribimos la cantidad calculada
        #amount = 0.0
        if not context:
            context = {}

        #amount = self._hook_get_amount(cr, uid, ids, amount, context=context)
        self._clean_payment_lines(cr, uid, ids, context=context)

        #self.write(cr, uid, ids, {'amount': amount}, context=context)
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
            elif voucher.type in ('sale', 'receipt'):
                debit = amount_in_company_currency
            if debit < 0: credit = -debit; debit = 0.0
            if credit < 0: debit = -credit; credit = 0.0
            sign = debit - credit < 0 and -1 or 1

            move_line = {
                    'name': pl.name or '/',
                    'debit': debit,
                    'credit': credit,
                    'account_id': pl.payment_mode_id.account_id.id,
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
            raise osv.except_osv(_('Voucher Error!'), _('Voucher Paid Amount and sum of different payment mode must be equal'))

        return move_lines

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

            # Escribimos el numero del voucher
            self.write(cr, uid, [voucher.id], {'number': name})

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

account_voucher()


class account_voucher_line(osv.osv):
    _name = 'account.voucher.line'
    _inherit = 'account.voucher.line'


    def onchange_amount(self, cr, uid, ids, amount, amount_unreconciled, context=None):
        vals = {}
        if amount:
            vals['reconcile'] = (round(amount, 2) == round(amount_unreconciled, 2))
        return {'value': vals}

account_voucher_line()
