###############################################################################
#   Copyright (C) 2008-2011  Thymbra
#   Copyright (c) 2012-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import time

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountCheckConfig(models.Model):
    '''
    Account Check Config
    '''
    _name = 'account.check.config'
    _description = 'Check Account Configuration'

    @api.multi
    def name_get(self):
        ret = []
        for config in self:
            ret.append((config.id, "%s: %s" % (config.company_id.name, config.account_id.name)))

        return ret

    account_id = fields.Many2one(comodel_name='account.account',
                                 string='Main Check Account',
                                 required=True,
                                 help="In Argentina, Valores a \
                                 Depositar is used, for example")
    deferred_account_id = fields.Many2one(comodel_name='account.account',
                                          string='Deferred Check Account',
                                          required=True)
    deferred_journal_id = fields.Many2one(comodel_name='account.journal',
                                          string='Deferred Check Journal',
                                          required=True)
    company_id = fields.Many2one(comodel_name='res.company',
                                 string='Company', required=True)

    _sql_constraints = [
        ('company_uniq', 'UNIQUE(company_id)', 'The configuration must be unique per company!'),
    ]


class AccountIssuedCheck(models.Model):
    '''
    Account Issued Check
    '''
    _name = 'account.issued.check'
    _description = 'Issued Checks'
    _rec_name = 'number'

    number = fields.Char(string='Check Number', size=20, required=True)
    amount = fields.Float(string='Amount Check', required=True)
    issue_date = fields.Date(string='Issue Date')
    payment_date = fields.Date(string='Payment Date',
                               help="Only if this check is post dated")
    reject_date = fields.Date(string='Reject Date')
    receiving_partner_id = fields.Many2one(comodel_name='res.partner',
                                           string='Receiving Entity',
                                           required=False, readonly=True)
    bank_id = fields.Many2one(comodel_name='res.bank',
                              string='Bank', required=True)
    signatory = fields.Char(string='Signatory', size=64)
    clearing = fields.Selection([('24', '24 hs'),
                                 ('48', '48 hs'),
                                 ('72', '72 hs')],
                                string='Clearing', default='24')
    # TODO: check domain
    account_bank_id = fields.Many2one(comodel_name='res.partner.bank',
                                      string='Bank Account')
    payment_order_id = fields.Many2one(comodel_name='account.payment.order',
                                       string='Voucher')
    payment_move_id = fields.Many2one(comodel_name='account.move',
                                      string='Payment Account Move')
    clearance_move_id = fields.Many2one(comodel_name='account.move',
                                        string='Clearance Account Move')
    accredited = fields.Boolean(string='Accredited',
                                compute='_compute_accredit_state')
    origin = fields.Char(string='Origin', size=64)
    crossed = fields.Boolean(string='Crossed')
    not_order = fields.Boolean(string='Not Order')
    note = fields.Text(string="Note")

    type = fields.Selection([
        ('common', 'Common'),
        ('postdated', 'Post-dated')],
        string='Check Type', default='common',
        help="If common, checks only have issued_date.\
        If post-dated they also have payment date")
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', required=True,
        readonly=True,
        default=lambda self: self.env.user.company_id.id)
    state = fields.Selection(
        [('draft', 'Draft'),
         ('waiting', 'Waiting Accreditation'),
         ('issued', 'Issued'),
         ('cancel', 'Cancelled'),
         ('rejected', 'Rejected')],
        string='State',
        default='draft')

    @api.depends('clearance_move_id')
    def _compute_accredit_state(self):
        for check in self:
            if check.clearance_move_id:
                check.accredited = True
            else:
                check.accredited = False

    @api.model
    def create_voucher_move_line(self):
        voucher = self.payment_order_id

        # Buscamos la cuenta contable para el asiento del cheque
        # Esta cuenta se corresponde con la cuenta de banco de donde
        # pertenece el cheque
        if self.type == 'postdated':
            # Buscamos la configuracion de cheques
            check_config_obj = self.env['account.check.config']
            config = check_config_obj.search([('company_id', '=', voucher.company_id.id)])
            if not len(config):
                err = _('There is no check configuration for this Company!')
                raise ValidationError(err)

            account_id = config.deferred_account_id.id
            date_maturity = self.payment_date
        else:
            account_id = self.account_bank_id.account_id.id
            date_maturity = voucher.date_due

        if not account_id:
            raise UserError(
                _("Error! Bank Account has no account" +
                  "configured. Please, configure an " +
                  "account for the bank account used for checks!"))

        # TODO: Chequear que funcione bien en multicurrency estas dos lineas de abajo
        company_currency = voucher.company_id.currency_id.id
        current_currency = voucher.currency_id.id
        amount_in_company_currency = voucher._convert_paid_amount_in_company_currency(self.amount)

        debit = credit = 0.0
        if voucher.type in ('purchase', 'payment'):
            credit = amount_in_company_currency
        elif voucher.type in ('sale', 'receipt'):
            debit = amount_in_company_currency
        if debit < 0:
            credit = -debit
            debit = 0.0
        if credit < 0:
            debit = -credit
            credit = 0.0
        sign = debit - credit < 0 and -1 or 1

        # Creamos la linea contable perteneciente al cheque
        if self.number:
            reference = _('Issued Check %s') % (self.number or '/')
        else:
            reference = _('Checkbook Number %s') % (self.checkbook_id.name or '/')

        move_line = {
            'name': reference,
            'debit': debit,
            'credit': credit,
            'account_id': account_id,
            'journal_id': voucher.journal_id.id,
            'period_id': voucher.period_id.id,
            'partner_id': voucher.partner_id.id,
            'currency_id': company_currency != current_currency and current_currency or False,
            'amount_currency': company_currency != current_currency and sign * self.amount or 0.0,
            'date': voucher.date,
            'date_maturity': date_maturity,
        }

        return move_line

    @api.multi
    def cancel_check(self):
        self.write({'state': 'cancel'})

    @api.multi
    def unlink(self):
        for check in self:
            if check.state != 'draft':
                raise UserError(_("Check Error! You cannot delete an " +
                                  "issued check that is not in Draft " +
                                  "state [See %s].") % (check.payment_order_id))
        return super(AccountIssuedCheck, self).unlink()

    @api.multi
    def accredit_checks(self):
        #TODO: create the corresponding moves
        for check in self:
            if check.state != "waiting":
                raise ValidationError(_("Check %s can't be accredited!") % check.number)

        for check in self:
            company = self.env.user.company_id
            check_conf_obj = self.env['account.check.config']
            def_check_account = check_conf_obj.search([
                ('company_id', '=', company.id)]).deferred_account_id
            def_check_journal = check_conf_obj.search([
                ('company_id', '=', company.id)]).deferred_journal_id
            if not def_check_journal:
                raise UserError(_("Error! There is no Journal \
                    configured for deferred checks."))

            current_date = time.strftime('%Y-%m-%d')

            period_obj = self.env['date.period']
            current_period = period_obj.search([
                ('date_from', '<=', current_date),
                ('date_to', '>=', current_date)])

            move_line_obj = self.env['account.move.line']
            move_obj = self.env['account.move']
            name_ref = 'Clearance Check ' + check.number
            move_vals = {
                'ref': name_ref,
                'journal_id': def_check_journal.id,
            }
            move_id = move_obj.create(move_vals)

            check.write({'clearance_move_id': move_id.id})

            # Creamos la línea contable que iguala el pago del cheque
            check_move_line_vals = {
                'journal_id': def_check_journal.id,
                'period_id': current_period.id,
                'date': current_date,
                'name': name_ref,
                'account_id': def_check_account.id,
                'debit': check.amount,
                'move_id': move_id.id,
            }

            clearance_move_line = move_line_obj.with_context({'check_move_validity': False}).create(check_move_line_vals)

            # Creamos la línea contable que refiere a la acreditación por parte del banco
            bank_move_line_vals = {
                'journal_id': def_check_journal.id,
                'period_id': current_period.id,
                'date': current_date,
                'name': name_ref,
                'account_id': check.checkbook_id.bank_account_id.account_id.id,
                'credit': check.amount,
                'move_id': move_id.id,
            }

            move_line_obj.with_context({'check_move_validity': False}).create(bank_move_line_vals)

            move_lines_to_reconcile = []
            payment_move_line = move_line_obj.search([
                ('issued_check_id', '=', check.id)])
            move_lines_to_reconcile.append(payment_move_line.id)
            move_lines_to_reconcile.append(clearance_move_line.id)
            reconcile_recordset = move_line_obj.browse(move_lines_to_reconcile)
            reconcile_recordset.reconcile()

        return self.write({"state": "issued"})

    def accredit_checks_cron_task(self):
        """ Search postdated checks and accredit them. This method is meant to be used by a cron
        task.
        """
        # on multicompany installations you must configure a cron task for each company or run it
        # as a multicompany user.
        company_ids = self.env.user.company_ids.ids or [self.env.user.company_id.id]
        checks = self.search(
            [
                ("type", "=", "postdated"),
                ("state", "=", "waiting"),
                ("payment_date", "<=", fields.Date.context_today(self)),
                ("company_id", "in", company_ids),
            ],
            order="number",
        )

        return checks.accredit_checks()

    # TODO
    @api.multi
    def break_conciliation(self):
        for check in self:
            if check.state != "issued":
                raise ValidationError(_("Can't break conciliation of a not issued check!"))
            if not check.accredited:
                raise ValidationError(_("Can't break conciliation of a not accredited check!"))
        for check in self:
            move = check.clearance_move_id
            move.line_ids.remove_move_reconcile()
            move.button_cancel()
            move.unlink()
            check.write({'state': 'waiting'})

    @api.multi
    def reject_check(self):
        self.write({
            'state': 'rejected',
        })
        return True


class AccountThirdCheck(models.Model):
    '''
    Account Third Check
    '''
    _name = 'account.third.check'
    _description = 'Third Checks'
    _rec_name = 'number'

    number = fields.Char(string='Check Number', size=20,
                         readonly=True, required=True,
                         states={'draft': [('readonly', False)]})
    amount = fields.Float(string='Check Amount',
                          readonly=True,
                          required=True,
                          states={'draft': [('readonly', False)]})
    receipt_date = fields.Date(string='Receipt Date',
                               readonly=True,
                               required=True,
                               states={'draft': [('readonly', False)]},
                               default=lambda *a: time.strftime('%Y-%m-%d'))
    issue_date = fields.Date(string='Issue Date',
                             readonly=True,
                             required=True,
                             states={'draft': [('readonly', False)]})
    payment_date = fields.Date(string='Payment Date',
                               readonly=True,
                               states={'draft': [('readonly', False)]})
    endorsement_date = fields.Date(string='Endorsement Date',
                                   readonly=True,
                                   states={'wallet': [('readonly', False)]})
    deposit_date = fields.Date(string='Deposit Date',
                               readonly=True,
                               states={'wallet': [('readonly', False)]})
    source_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Source Partner',
        required=False,
        readonly=True,
        states={'draft': [('readonly', False)]})
    destiny_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Destiny Partner',
        states={'delivered': [('required', True)]})
    state = fields.Selection([('draft', 'Draft'),
                              ('wallet', 'In Wallet'),
                              ('deposited', 'Deposited'),
                              ('delivered', 'Delivered'),
                              ('rejected', 'Rejected'),
                              ('cancel', 'Cancelled')],
                             string='State', readonly=True, default='draft')
    bank_id = fields.Many2one(comodel_name='res.bank', string='Bank',
                              required=True, readonly=True,
                              states={'draft': [('readonly', False)]})
    #'vat': fields.Char('Vat', size=15, required=True),
    #'on_order': fields.Char('On Order', size=64),
    signatory = fields.Char(string='Signatory', size=64)
    clearing = fields.Selection([('24', '24 hs'),
                                 ('48', '48 hs'),
                                 ('72', '72 hs')],
                                string='Clearing', default='24')
    origin = fields.Char(string='Origin', size=64)
    dest = fields.Char(string='Destiny', size=64)
    deposit_bank_id = fields.Many2one(comodel_name='res.partner.bank',
                                      string='Deposit Account')
    source_payment_order_id = fields.Many2one(
        comodel_name='account.payment.order',
        string='Source Voucher',
        ondelete="cascade", readonly=True)
    debit_note_id = fields.Many2one(
        comodel_name='account.invoice',
        string='Debit Note', readonly=True,
        help="In case of rejection of the third check")
    type = fields.Selection([('common', 'Common'),
                             ('postdated', 'Post-dated')],
                            string='Check Type', readonly=True,
                            states={'draft': [('readonly', False)]},
                            default='common',
                            help="If common, checks only have issued_date. \
                            If post-dated they also have payment date")
    note = fields.Text(string='Additional Information')
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company',
        required=True, readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user.company_id.id)
    signatory_vat = fields.Char(string='Signatory VAT', size=64)
    signatory_account = fields.Char(string='Signatory account', size=64)
    deposit_slip = fields.Char(string='Deposit Slip', size=64)
    crossed = fields.Boolean(string='Crossed')
    not_order = fields.Boolean(string='Not Order')
    bank_branch = fields.Char(string='Bank Branch', size=64)
    zip = fields.Char(string='Zip Code', size=64)

    @api.model
    def create_voucher_move_line(self, voucher):
        check_config_obj = self.env['account.check.config']

        # Buscamos la configuracion de cheques
        config = check_config_obj.search([
            ('company_id', '=', voucher.company_id.id)])
        if not len(config):
            raise UserError(
                _(' ERROR! There is no check configuration for this Company!'))

        # TODO: Chequear que funcione bien en multicurrency estas dos lineas de abajo
        company_currency = voucher.company_id.currency_id.id
        current_currency = voucher.currency_id.id

        amount_in_company_currency = voucher._convert_paid_amount_in_company_currency(self.amount)

        debit = credit = 0.0
        if voucher.type in ('purchase', 'payment'):
            credit = amount_in_company_currency
        elif voucher.type in ('sale', 'receipt'):
            debit = amount_in_company_currency
        if debit < 0:
            credit = -debit
            debit = 0.0
        if credit < 0:
            debit = -credit
            credit = 0.0
        sign = debit - credit < 0 and -1 or 1

        # Creamos la linea contable perteneciente al cheque
        move_line = {
            'name': _('Third Check ') + self.number or '/',
            'debit': debit,
            'credit': credit,
            'account_id': config.account_id.id,
            'journal_id': voucher.journal_id.id,
            'period_id': voucher.period_id.id,
            'partner_id': voucher.partner_id.id,
            'currency_id': company_currency != current_currency and current_currency or False,
            'amount_currency': company_currency != current_currency and sign * self.amount or 0.0,
            'date': voucher.date,
            'date_maturity': self.payment_date or self.issue_date,
        }

        return move_line

    @api.multi
    def to_wallet(self):
        # Funcion llamada al validar un pago de cliente que contenga cheques
        for check in self:
            voucher = check.source_payment_order_id
            if not voucher:
                raise UserError(_('Check Error! Check has to \
                    be associated with a voucher'))

            partner_id = voucher.partner_id.id
            vals = {}
            if voucher.type == 'receipt':
                vals['source_partner_id'] = partner_id

            if not check.origin:
                vals['origin'] = voucher.reference
            vals['state'] = 'wallet'

            # Si es cheque comun tomamos la fecha de emision
            # como feche de pago tambien porque seria un cheque al dia
            if check.type == 'common':
                vals['payment_date'] = check.issue_date

            check.write(vals)
        return True

    @api.multi
    def return_wallet(self):
        # Todos los cheques tienen que estar en delivered
        for check in self:
            if check.state != 'delivered':
                raise UserError(_("Third Check Error! You cannot return to \
                    wallet a check if it is not in Delivered state"))
        vals = {'state': 'wallet', 'endorsement_date': False, 'destiny_partner_id': False, 'dest': ''}
        self.write(vals)
        return True

    @api.multi
    def unlink(self):
        for check in self:
            if check.state != 'draft':
                raise UserError(_('Check Error! You cannot delete a third \
                    check that is not in Draft state [See %s].') %
                                (check.source_payment_order_id))
        return super(AccountThirdCheck, self).unlink()

    @api.multi
    def cancel_check(self):
        # Todos los cheques tienen que estar en draft o wallet
        for check in self:
            if check.state not in ('draft', 'wallet'):
                raise UserError(_("Third Check Error! You cannot cancel \
                    check if it is not in Draft or in Wallet"))
        self.write({'state': 'cancel'})
        return True

    @api.multi
    def check_delivered(self):
        # Transicion efectuada al validar un pago a proveedores que entregue
        # cheques de terceros
        voucher_obj = self.env['account.payment.order']
        vals = {'state': 'delivered'}
        for check in self:
            voucher = voucher_obj.search([
                ('third_check_ids', '=', check.id),
                ('state', '!=', 'cancel')])
            # voucher = voucher_obj.browse(cr, uid, payment_order_ids[0], context=context)  # check.dest_payment_order_id

            if not check.endorsement_date:
                vals['endorsement_date'] = voucher.date or time.strftime('%Y-%m-%d')
            vals['destiny_partner_id'] = voucher.partner_id.id

            if not check.dest:
                vals['dest'] = voucher.reference

            check.write(vals)
        return True

    @api.multi
    def deposit_check(self):
        # Transicion efectuada via wizard
        self.write({
            'state': 'deposited',
        })
        return True

    @api.multi
    def reject_check(self):
        self.write({
            'state': 'rejected',
        })
        return True
