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

import time
from tools.translate import _
from osv import fields, osv


class account_check_config(osv.osv):
    '''
    Account Check Config
    '''
    _name = 'account.check.config'
    _description = 'Check Account Configuration'

    _columns = {
        'account_id': fields.many2one('account.account', 'Main Check Account', required=True,
                                       help="In Argentina, Valores a Depositar is used, for example"),
        'company_id': fields.many2one('res.company', 'Company', required=True),
            }

    _sql_constraints = [
        ('company_uniq', 'UNIQUE(company_id)', 'The configuration must be unique per company!'),
    ]

account_check_config()


class account_issued_check(osv.osv):
    '''
    Account Issued Check
    '''
    _name = 'account.issued.check'
    _description = 'Issued Checks'
    _rec_name = 'number'

    _columns = {
        'number': fields.char('Check Number', size=20, required=True),
        'amount': fields.float('Amount Check', required=True),
        'issue_date': fields.date('Issue Date', required=True),
        'payment_date': fields.date('Payment Date', help="Only if this check is post dated"),
        'receiving_partner_id': fields.many2one('res.partner',
            'Receiving Entity', required=False, readonly=True),
        'bank_id': fields.many2one('res.bank', 'Bank', required=True),
        #'on_order': fields.char('On Order', size=64),
        'signatory': fields.char('Signatory', size=64),
        'clearing': fields.selection((
                ('24', '24 hs'),
                ('48', '48 hs'),
                ('72', '72 hs'),
            ), 'Clearing'),
        'account_bank_id': fields.many2one('res.partner.bank', 'Bank Account'),
        'voucher_id': fields.many2one('account.voucher', 'Voucher'),
        'issued': fields.boolean('Issued'),
        'type': fields.selection([('common', 'Common'),('postdated', 'Post-dated')], 'Check Type',
            help="If common, checks only have issued_date. If post-dated they also have payment date"),
    }

    _defaults = {
        'clearing': lambda *a: '24',
        'type': 'common',
    }

    def create_voucher_move_line(self, cr, uid, check, voucher, context={}):
        currency_pool = self.pool.get('res.currency')

        context_multi_currency = context.copy()
        context_multi_currency.update({'date': voucher.date})

        # Buscamos la cuenta contable para el asiento del cheque
        # Esta cuenta se corresponde con la cuenta de banco de donde
        # pertenece el cheque
        account_id = check.account_bank_id.account_id.id
        if not account_id:
            raise osv.except_osv(_("Error"), _("Bank Account has no account configured. Please, configure an account for the bank account used for checks!"))

        # TODO: Chequear que funcione bien en multicurrency estas dos lineas de abajo
        company_currency = voucher.journal_id.company_id.currency_id.id
        current_currency = voucher.currency_id.id

        credit = 0.0
        debit = 0.0
        if voucher.type in ('purchase', 'payment'):
            credit = currency_pool.compute(cr, uid, current_currency, company_currency, check.amount, context=context_multi_currency)
        # TODO: Deberia ser siempre voucher.type = 'purchase' porque son
        # cheques propios. Pero por las dudas, dejamos este codigo
        # hasta que se pruebe y testee mas
        elif voucher.type in ('sale', 'receipt'):
            debit = currency_pool.compute(cr, uid, current_currency, company_currency, check.amount, context=context_multi_currency)

        if debit < 0:
            credit = -debit
            debit = 0.0
        if credit < 0:
            debit = -credit
            credit = 0.0
        sign = debit - credit < 0 and -1 or 1

        # Creamos la linea contable perteneciente al cheque
        move_line = {
            'name': 'Ch. ' + check.number or '/',
            'debit': debit,
            'credit': credit,
            'account_id': account_id,
            'journal_id': voucher.journal_id.id,
            'period_id': voucher.period_id.id,
            'partner_id': voucher.partner_id.id,
            'currency_id': company_currency <> current_currency and  current_currency or False,
            'amount_currency': company_currency <> current_currency and sign * check.amount or 0.0,
            'date': voucher.date,
            'date_maturity': voucher.date_due
        }

        return move_line

account_issued_check()


class account_third_check(osv.osv):
    '''
    Account Third Check
    '''
    _name = 'account.third.check'
    _description = 'Manage Checks'
    _rec_name = 'number'

    _columns = {
        'number': fields.char('Check Number', size=20, required=True),
        'amount': fields.float('Check Amount', required=True),
        'date_in': fields.date('Date In', required=True),
        'date': fields.date('Check Date', required=True),
        'date_out': fields.date('Date Out', readonly=True),
        'source_partner_id': fields.many2one('res.partner', 'Source Partner',
            required=False, readonly=True),
        'destiny_partner_id': fields.many2one('res.partner', 'Destiny Partner',
            readonly=False, required=False,
            states={'delivered': [('required', True)]}),
        'state': fields.selection((
                ('draft', 'Draft'),
                ('C', 'En Cartera'),
                ('deposited', 'Deposited'),
                ('delivered', 'Delivered'),
                ('rejected', 'Rejected'),
            ), 'State', required=True),
        'bank_id': fields.many2one('res.bank', 'Bank', required=True),
        'vat': fields.char('Vat', size=15, required=True),
        'on_order': fields.char('On Order', size=64),
        'signatory': fields.char('Signatory', size=64),
        'clearing': fields.selection((
                ('24', '24 hs'),
                ('48', '48 hs'),
                ('72', '72 hs'),
            ), 'Clearing'),
        'origin': fields.char('Origen', size=64),
        'account_bank_id': fields.many2one('res.partner.bank',
            'Destiny Account'),
        'voucher_id': fields.many2one('account.voucher', 'Voucher'),
        'reject_debit_note': fields.many2one('account.invoice',
            'Reject Debit Note'),
    }

    _defaults = {
        'date_in': lambda *a: time.strftime('%Y-%m-%d'),
        'state': lambda *a: 'draft',
        'clearing': lambda *a: '24',
    }

    def create_voucher_move_line(self, cr, uid, check, voucher, context={}):
        currency_pool = self.pool.get('res.currency')
        check_config_obj = self.pool.get('account.check.config')

        context_multi_currency = context.copy()
        context_multi_currency.update({'date': voucher.date})

        # Buscamos la configuracion de cheques
        res = check_config_obj.search(cr, uid, [('company_id', '=', voucher.company_id.id)])
        if not len(res):
            raise osv.except_osv(_(' ERROR!'), _('There is no check configuration for this Company!'))

        config = check_config_obj.browse(cr, uid, res[0])

        # TODO: Chequear que funcione bien en multicurrency estas dos lineas de abajo
        company_currency = voucher.journal_id.company_id.currency_id.id
        current_currency = voucher.currency_id.id

        credit = 0.0
        debit = 0.0
        if voucher.type in ('purchase', 'payment'):
            credit = currency_pool.compute(cr, uid, current_currency, company_currency, check.amount, context=context_multi_currency)
        elif voucher.type in ('sale', 'receipt'):
            debit = currency_pool.compute(cr, uid, current_currency, company_currency, check.amount, context=context_multi_currency)

        if debit < 0:
            credit = -debit
            debit = 0.0
        if credit < 0:
            debit = -credit
            credit = 0.0
        sign = debit - credit < 0 and -1 or 1

        # Creamos la linea contable perteneciente al cheque
        move_line = {
            'name': 'Ch. ' + check.number or '/',
            'debit': debit,
            'credit': credit,
            'account_id': config.account_id.id,
            'journal_id': voucher.journal_id.id,
            'period_id': voucher.period_id.id,
            'partner_id': voucher.partner_id.id,
            'currency_id': company_currency <> current_currency and  current_currency or False,
            'amount_currency': company_currency <> current_currency and sign * check.amount or 0.0,
            'date': voucher.date,
            'date_maturity': voucher.date_due
        }

        return move_line

    def wkf_cartera(self, cr, uid, ids, context=None):
        # Transicion efectuada al validar un pago de cliente que contenga
        # cheques
        for check in self.browse(cr, uid, ids):
            if check.voucher_id:
                source_partner_id = check.voucher_id.partner_id.id
            else:
                source_partner_id = None
            check.write({
                'state': 'C',
                'source_partner_id': source_partner_id,
            })
        return True

    def wkf_delivered(self, cr, uid, ids, context=None):
        # Transicion efectuada al validar un pago a proveedores que entregue
        # cheques de terceros
        for check in self.browse(cr, uid, ids):
            check.write({
                'state': 'delivered',
            })
        return True

    def wkf_deposited(self, cr, uid, ids, context=None):
        # Transicion efectuada via wizard
        for check in self.browse(cr, uid, ids):
            check.write({
                'state': 'deposited',
            })
        return True

    def wkf_rejected(self, cr, uid, ids, context=None):
        for check in self.browse(cr, uid, ids):
            check.write({
                'state': 'rejected',
            })
        return True

account_third_check()
