# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2008-2011  Thymbra
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
        'issue_date': fields.date('Issue Date'),
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
        'origin': fields.char('Origin', size=64),
        'type': fields.selection([('common', 'Common'),('postdated', 'Post-dated')], 'Check Type',
            help="If common, checks only have issued_date. If post-dated they also have payment date"),
    }

    _defaults = {
        'clearing': lambda *a: '24',
        'type': 'common',
    }

    def create_voucher_move_line(self, cr, uid, check, voucher, context={}):
        voucher_obj = self.pool.get('account.voucher')

        # Buscamos la cuenta contable para el asiento del cheque
        # Esta cuenta se corresponde con la cuenta de banco de donde
        # pertenece el cheque
        account_id = check.account_bank_id.account_id.id
        if not account_id:
            raise osv.except_osv(_("Error"), _("Bank Account has no account configured. Please, configure an account for the bank account used for checks!"))

        # TODO: Chequear que funcione bien en multicurrency estas dos lineas de abajo
        company_currency = voucher.company_id.currency_id.id
        current_currency = voucher.currency_id.id

        amount_in_company_currency =  voucher_obj._convert_paid_amount_in_company_currency(cr, uid, voucher, check.amount, context=context)
        #amount_in_company_currency = currency_obj.compute(cr, uid, current_currency, voucher.company_id.currency_id.id, check.amount, context=context)

        debit = credit = 0.0
        if voucher.type in ('purchase', 'payment'):
            credit = amount_in_company_currency
        elif voucher.type in ('sale', 'receipt'):
            debit = amount_in_company_currency
        if debit < 0: credit = -debit; debit = 0.0
        if credit < 0: debit = -credit; credit = 0.0
        sign = debit - credit < 0 and -1 or 1

        # Creamos la linea contable perteneciente al cheque
        move_line = {
            'name': 'Issued Check ' + check.number or '/',
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
    _description = 'Third Checks'
    _rec_name = 'number'

    _columns = {
        'number': fields.char('Check Number', size=20, readonly=True, required=True, states={'draft': [('readonly', False)]}),
        'amount': fields.float('Check Amount', readonly=True, required=True, states={'draft': [('readonly', False)]}),
        'receipt_date': fields.date('Receipt Date', readonly=True, required=True, states={'draft': [('readonly', False)]}), # Fecha de ingreso
        'issue_date': fields.date('Issue Date', readonly=True, required=True, states={'draft': [('readonly', False)]}), # Fecha de emision
        'payment_date': fields.date('Payment Date', readonly=True, states={'draft': [('readonly', False)]}), # Fecha de pago diferido
        'endorsement_date': fields.date('Endorsement Date', readonly=True, states={'wallet': [('readonly', False)]}), # Fecha de Endoso
        'deposit_date': fields.date('Deposit Date', readonly=True, states={'wallet': [('readonly', False)]}), # Fecha de Deposito
        'source_partner_id': fields.many2one('res.partner', 'Source Partner', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'destiny_partner_id': fields.many2one('res.partner', 'Destiny Partner', states={'delivered': [('required', True)]}),
        'state': fields.selection((
                ('draft', 'Draft'),
                ('wallet', 'In Wallet'),
                ('deposited', 'Deposited'),
                ('delivered', 'Delivered'),
                ('rejected', 'Rejected'),
            ), 'State', readonly=True),
        'bank_id': fields.many2one('res.bank', 'Bank', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        #'vat': fields.char('Vat', size=15, required=True),
        #'on_order': fields.char('On Order', size=64),
        'signatory': fields.char('Signatory', size=64),
        'clearing': fields.selection((
                ('24', '24 hs'),
                ('48', '48 hs'),
                ('72', '72 hs'),
            ), 'Clearing'),
        'origin': fields.char('Origin', size=64),
        'dest': fields.char('Destiny', size=64),
        'deposit_bank_id': fields.many2one('res.partner.bank',
            'Deposit Account'),
        'source_voucher_id': fields.many2one('account.voucher', 'Source Voucher', readonly=True),
        'type': fields.selection([('common', 'Common'),('postdated', 'Post-dated')], 'Check Type',
            readonly=True, states={'draft': [('readonly', False)]},
            help="If common, checks only have issued_date. If post-dated they also have payment date"),
    }

    _defaults = {
        'receipt_date': lambda *a: time.strftime('%Y-%m-%d'),
        'state': lambda *a: 'draft',
        'type': lambda *a: 'common',
        'clearing': lambda *a: '24',
    }

    def create_voucher_move_line(self, cr, uid, check, voucher, context={}):
        currency_obj = self.pool.get('res.currency')
        check_config_obj = self.pool.get('account.check.config')

        # Buscamos la configuracion de cheques
        res = check_config_obj.search(cr, uid, [('company_id', '=', voucher.company_id.id)])
        if not len(res):
            raise osv.except_osv(_(' ERROR!'), _('There is no check configuration for this Company!'))

        config = check_config_obj.browse(cr, uid, res[0])

        # TODO: Chequear que funcione bien en multicurrency estas dos lineas de abajo
        company_currency = voucher.company_id.currency_id.id
        current_currency = voucher.currency_id.id

        amount_in_company_currency = currency_obj.compute(cr, uid, current_currency, voucher.company_id.currency_id.id, check.amount, context=context)

        debit = credit = 0.0
        if voucher.type in ('purchase', 'payment'):
            credit = amount_in_company_currency
        elif voucher.type in ('sale', 'receipt'):
            debit = amount_in_company_currency
        if debit < 0: credit = -debit; debit = 0.0
        if credit < 0: debit = -credit; credit = 0.0
        sign = debit - credit < 0 and -1 or 1

        # Creamos la linea contable perteneciente al cheque
        move_line = {
            'name': _('Third Check ') + check.number or '/',
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
            voucher = check.source_voucher_id
            if not voucher:
                raise osv.except_osv(_('Check Error!'), _('Check has to be associated with a voucher'))

            partner_id = voucher.partner_id.id
            vals = {}
            if voucher.type == 'receipt':
                vals['source_partner_id'] = partner_id

            if not check.origin:
                vals['origin'] = voucher.number
            vals['state'] = 'wallet'

            # Si es cheque comun tomamos la fecha de emision
            # como feche de pago tambien porque seria un cheque al dia
            if check.type == 'common':
                vals['payment_date'] = check.issue_date

            check.write(vals)
        return True

    def wkf_delivered(self, cr, uid, ids, context=None):
        # Transicion efectuada al validar un pago a proveedores que entregue
        # cheques de terceros
        voucher_obj = self.pool.get('account.voucher')
        vals = {'state': 'delivered'}
        for check in self.browse(cr, uid, ids):
            voucher_ids = voucher_obj.search(cr, uid, [('third_check_ids','=',check.id)], context=context)
            voucher = voucher_obj.browse(cr, uid, voucher_ids[0], context=context) #check.dest_voucher_id

            if not check.endorsement_date:
                vals['endorsement_date'] = voucher.date or time.strftime('%Y-%m-%d')
            vals['destiny_partner_id'] = voucher.partner_id.id

            if not check.dest:
                vals['dest'] = voucher.number

            check.write(vals)
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
