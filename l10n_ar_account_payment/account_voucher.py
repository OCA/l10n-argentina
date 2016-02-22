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

from openerp import models, fields, api, _
from openerp.osv import osv


class account_voucher(models.Model):

    _name = "account.voucher"
    _inherit = "account.voucher"

    payment_line_ids = fields.One2many('payment.mode.receipt.line', 'voucher_id', 'Payments Lines')
    journal_sequence = fields.Many2one('ir.sequence', 'Book', readonly=True, states={'draft': [('readonly', False)]})

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if context is None:
            context = {}
        return [(r['id'], (str("%s - %.2f" % (r['reference'], r['amount'])) or '')) for r in self.read(cr, uid, ids, ['reference', 'amount'], context, load='_classic_write')]

    @api.multi
    def _get_payment_lines_amount(self):
        amount = 0.0
        for payment_line in self.payment_line_ids:
            amount += float(payment_line.amount)
        return amount

    @api.onchange('payment_line_ids')
    def onchange_payment_line(self):
        amount = self._get_payment_lines_amount()
        self.amount = amount

    @api.multi
    def onchange_partner_id(self, partner_id, journal_id, amount, currency_id, ttype, date):
        res = super(account_voucher, self).onchange_partner_id(partner_id, journal_id, amount, currency_id, ttype, date)
        if not partner_id:
            res['value']['payment_line_ids'] = []
            return res
        if 'value' not in res:
            return res

        res2 = self._get_payment_lines_default(ttype, currency_id)
        res['value']['payment_line_ids'] = res2

        return res

    @api.model
    def _get_payment_lines_default(self, ttype, currency_id):
        pay_mod_pool = self.env['payment.mode.receipt']
        modes = pay_mod_pool.search([('type', '=', ttype), ('currency', '=', currency_id)])
        if not modes:
            return {}

        lines = []
        for mode in modes:
            lines.append({'name': mode.name, 'amount': 0.0, 'amount_currency': 0.0, 'payment_mode_id': mode.id, 'currency': mode.currency.id})

        return lines

    @api.one
    def _clean_payment_lines(self):
        for payment_line in self.payment_line_ids:
            if payment_line.amount == 0:
                payment_line.unlink()
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

    @api.multi
    def proforma_voucher(self):
        # Chequeamos si la writeoff_amount no es negativa
        if round(self.writeoff_amount, 2) < 0.0:
            raise osv.except_osv(_("Validate Error!"), _("Cannot validate a voucher with negative amount. Please check that Writeoff Amount is not negative."))

        self._clean_payment_lines()
        self.action_move_line_create()

        return True

    @api.multi
    def create_move_line_hook(self, move_id, move_lines):
        return move_lines

    @api.model
    def _convert_paid_amount_in_company_currency(self, amount):
        res = {}
        ctx = self._context.copy()
        ctx.update({'date': self.date})
        ctx.update({
            'voucher_special_currency': self.payment_rate_currency_id and self.payment_rate_currency_id.id or False,
            'voucher_special_currency_rate': self.currency_id.rate * self.payment_rate
        })
        currency = self.currency_id.with_context(ctx)
        company_currency = self.company_id.currency_id
        res = currency.compute(amount, company_currency)
        return res

    # Heredada para agregar un hook y los asientos para varias formas de pago
    @api.multi
    def create_move_lines(self, move_id, company_currency, current_currency):
        '''
        Return a dict to be use to create account move lines of given voucher.

        :param voucher_id: Id of voucher what we are creating account_move.
        :param move_id: Id of account move where this line will be added.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: mapping between fieldname and value of account move line to create
        :rtype: dict
        '''
        total_debit = total_credit = 0.0
        # TODO: is there any other alternative then the voucher type ??
        # ANSWER: We can have payment and receipt "In Advance".
        # TODO: Make this logic available.
        # -for sale, purchase we have but for the payment and receipt we do not have as based on the bank/cash journal we can not know its payment or receipt
        if self.type in ('purchase', 'payment'):
            total_credit = self.paid_amount_in_company_currency
        elif self.type in ('sale', 'receipt'):
            total_debit = self.paid_amount_in_company_currency
        if total_debit < 0:
            total_credit = - total_debit
            total_debit = 0.0
        if total_credit < 0:
            total_debit = -total_credit
            total_credit = 0.0
        sign = total_debit - total_credit < 0 and -1 or 1

        # Creamos una move_line por payment_line
        move_lines = []
        for pl in self.payment_line_ids:
            if pl.amount == 0.0:
                continue

            amount_in_company_currency = self._convert_paid_amount_in_company_currency(pl.amount)

            debit = credit = 0.0
            if self.type in ('purchase', 'payment'):
                credit = amount_in_company_currency
            elif self.type in ('sale', 'receipt'):
                debit = amount_in_company_currency
            if debit < 0:
                credit = -debit
                debit = 0.0
            if credit < 0:
                debit = -credit
                credit = 0.0
            sign = debit - credit < 0 and -1 or 1

            move_line = {
                'name': pl.name or '/',
                'debit': debit,
                'credit': credit,
                'account_id': pl.payment_mode_id.account_id.id,
                'move_id': move_id,
                'journal_id': self.journal_id.id,
                'period_id': self.period_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': company_currency <> current_currency and current_currency or False,
                'amount_currency': company_currency <> current_currency and sign * pl.amount or 0.0,
                'date': self.date,
                'date_maturity': self.date_due
            }

            move_lines.append(move_line)

        # Creamos un hook para agregar los demas asientos contables de otros modulos
        self.create_move_line_hook(move_id, move_lines)

        # Recorremos las lineas para  hacer un chequeo de debit y credit contra total_debit y total_credit
        amount_credit = 0.0
        amount_debit = 0.0
        for line in move_lines:
            amount_credit += line['credit']
            amount_debit += line['debit']

        if round(amount_credit, 3) != round(total_credit, 3) or round(amount_debit, 3) != round(total_debit, 3):
            if self.type in ('purchase', 'payment'):
                amount_credit -= amount_debit
                amount_debit -= amount_debit
            else:
                amount_debit -= amount_credit
                amount_credit -= amount_credit

            if round(amount_credit, 3) != round(total_credit, 3) or round(amount_debit, 3) != round(total_debit, 3):
                raise osv.except_osv(_('Voucher Error!'), _('Voucher Paid Amount and sum of different payment mode must be equal'))

        return move_lines

    @api.model
    def _update_move_reference(self, move_id, ref):
        cr = self.env.cr
        cr.execute('UPDATE account_move SET ref=%s ' \
                    'WHERE id=%s', (ref, move_id))

        cr.execute('UPDATE account_move_line SET ref=%s ' \
                'WHERE move_id=%s', (ref, move_id))

        cr.execute('UPDATE account_analytic_line SET ref=%s ' \
                'FROM account_move_line ' \
                'WHERE account_move_line.move_id = %s ' \
                    'AND account_analytic_line.move_id = account_move_line.id',
                    (ref, move_id))
        self.env.invalidate_all()  # Invalidamos la cache
        return True

    @api.multi
    def action_move_line_create(self):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        move_pool = self.env['account.move']
        move_line_pool = self.env['account.move.line']
        for voucher in self:
            if voucher.move_id:
                continue
            company_currency = self._get_company_currency(voucher.id)
            current_currency = self._get_current_currency(voucher.id)
            # we select the context to use accordingly if it's a multicurrency case or not
            context = self._sel_context(voucher.id)
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = context.copy()
            ctx.update({'date': voucher.date})
            # Create the account move record.
            move_recordset = move_pool.with_context(ctx).create(self.account_move_get(voucher.id))
            # Get the name of the account_move just created
            name = move_recordset.name
            move_id = move_recordset.id

            # Escribimos el numero del voucher
            # Seteamos el numero de la OP
            voucher_vals = {'number': 'name'}
            if voucher.type in ('payment', 'receipt'):
                if not voucher.reference:
                    ref = self.env['ir.sequence'].next_by_id(voucher.journal_sequence.id)
                    voucher_vals['reference'] = ref
                    self._update_move_reference(move_id, ref)

            voucher.write(voucher_vals)

            if voucher.type in ('payment', 'receipt'):
                # Creamos las lineas contables de todas las formas de pago, etc
                move_line_vals = self.create_move_lines(move_id, company_currency, current_currency)
                line_total = 0.0
                for vals in move_line_vals:
                    line_total += vals['debit'] - vals['credit']
                    move_line_pool.create(vals)
            else:  # ('sale', 'purchase')
                # Create the first line of the voucher
                move_line_brw = move_line_pool.with_context(ctx).create(self.first_move_line_get(voucher.id, move_id, company_currency, current_currency))
                line_total = move_line_brw.debit - move_line_brw.credit

            # move_line_brw = move_line_pool.browse(cr, uid, move_line_id, context=context)
            # line_total = move_line_brw.debit - move_line_brw.credit
            rec_list_ids = []
            if voucher.type == 'sale':
                line_total = line_total - self._convert_amount(voucher.tax_amount, voucher.id)
            elif voucher.type == 'purchase':
                line_total = line_total + self._convert_amount(voucher.tax_amount, voucher.id)
            # Create one move line per voucher line where amount is not 0.0
            line_total, rec_list_ids = self.voucher_move_line_create(voucher.id, line_total, move_id, company_currency, current_currency)

            # Create the writeoff line if needed
            ml_writeoff = self.writeoff_move_line_get(voucher.id, line_total, move_id, name, company_currency, current_currency)
            if ml_writeoff:
                move_line_pool.create(ml_writeoff)

            # We post the voucher.
            self.write({
                'move_id': move_id,
                'state': 'posted',
                'number': name,
            })
            if voucher.journal_id.entry_posted:
                move_recordset.post()
            # We automatically reconcile the account move lines.
            reconcile = False
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    reconcile = self.pool.get('account.move.line').reconcile_partial(self.env.cr, self.env.user.id, rec_ids, writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id)


            # Borramos las lineas que estan en 0
            for line in voucher.line_ids:
                if not line.amount:
                    line.unlink()

        return True

    @api.multi
    def recompute_voucher_lines(self, partner_id, journal_id, price, currency_id, ttype, date):
        default = super(account_voucher, self).recompute_voucher_lines(partner_id, journal_id, price, currency_id, ttype, date)
        ml_obj = self.env['account.move.line']

        for vals in default['value']['line_dr_ids'] + default['value']['line_cr_ids']:
            if type(vals) == dict and vals['move_line_id']:
                ml = ml_obj.browse(vals['move_line_id'])
                vals['invoice_id'] = ml.invoice.id or False
                vals['ref'] = ml.ref
        return default

account_voucher()


class account_voucher_line(models.Model):
    _name = 'account.voucher.line'
    _inherit = 'account.voucher.line'

    invoice_id = fields.Many2one('account.invoice', string='Invoice')
    ref = fields.Char('Reference', size=64)

    def onchange_amount(self, cr, uid, ids, amount, amount_unreconciled, context=None):
        vals = {}
        if amount:
            vals['reconcile'] = (round(amount, 2) == round(amount_unreconciled, 2))
        return {'value': vals}

account_voucher_line()
