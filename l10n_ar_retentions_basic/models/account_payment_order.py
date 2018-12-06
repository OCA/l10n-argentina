###############################################################################
#    Copyright (c) 2011-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp


class RetentionTaxLine(models.Model):
    _name = "retention.tax.line"
    _description = "Retention Tax Line"

    # TODO: Tal vaz haya que ponerle estados a este objeto
    # para manejar tambien propiedades segun estados
    name = fields.Char(string='Retention', size=64)
    date = fields.Date(string='Date', index=True)
    payment_order_id = fields.Many2one(comodel_name='account.payment.order',
                                       string='Payment Order',
                                       ondelete='cascade')
    voucher_number = fields.Char(string='Reference', size=64)
    account_id = fields.Many2one(comodel_name='account.account',
                                 string='Tax Account',
                                 required=True,
                                 domain=[('type', '<>', 'view'),
                                         ('type', '<>', 'income'),
                                         ('type', '<>', 'closed')])
    base = fields.Float(string='Base', digits=dp.get_precision('Account'))
    amount = fields.Float(string='Amount', digits=dp.get_precision('Account'))
    retention_id = fields.Many2one(comodel_name='retention.retention',
                                   string='Retention Configuration',
                                   required=True,
                                   help="Retention configuration used for this \
                                   retention tax, where all the configuration \
                                   resides. Accounts, Tax Codes, etc.")
    base_amount = fields.Float(comodel_name='Base Code Amount',
                               digits=dp.get_precision('Account'))
    tax_amount = fields.Float(string='Tax Code Amount',
                              digits=dp.get_precision('Account'))
    company_id = fields.Many2one(string='Company',
                                 related='account_id.company_id',
                                 store=True, readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner',
                                 string='Partner', required=False)
    vat = fields.Char(string='CIF/NIF',
                      related='partner_id.vat',
                      readonly=True)
    certificate_no = fields.Char(string='Certificate No.',
                                 required=False, size=32)
    state_id = fields.Many2one(comodel_name='res.country.state',
                               string="State/Province")

    @api.onchange('retention_id')
    def onchange_retention(self):
        retention = self.retention_id
        if retention.id:
            self.name = retention.name
            self.account_id = retention.tax_id.account_id.id
            # self.base_code_id = retention.tax_id.base_code_id.id
            # self.tax_code_id = retention.tax_id.tax_code_id.id

            if retention.state_id:
                self.state_id = retention.state_id.id
            else:
                self.state_id = False

    @api.multi
    def create_voucher_move_line(self):
        """
        Params
        self = retention.tax.line
        """
        voucher = self.payment_order_id
        self.ensure_one()
        retention = self

        if retention.amount == 0.0:
            return {}

        # Chequeamos si esta seteada la fecha,
        # sino le ponemos la fecha del voucher
        retention_vals = {}
        if not retention.date:
            retention_vals['date'] = voucher.date

        company_currency = voucher.company_id.currency_id.id
        current_currency = voucher.currency_id.id

        tax_amount_in_company_currency = \
            voucher._convert_paid_amount_in_company_currency(retention.amount)

        debit = credit = 0.0

        # Lo escribimos en el objeto retention_tax_line
        # retention_vals['tax_amount'] = tax_amount_in_company_currency
        # retention_vals['base_amount'] = base_amount_in_company_currency

        retention.write(retention_vals)

        debit = credit = 0.0
        if voucher.type in ('purchase', 'payment'):
            credit = tax_amount_in_company_currency
        elif voucher.type in ('sale', 'receipt'):
            debit = tax_amount_in_company_currency
        if debit < 0:
            credit = -debit
            debit = 0.0
        if credit < 0:
            debit = -credit
            credit = 0.0
        sign = debit - credit < 0 and -1 or 1

        self.apply_retention_sequence()

        # Creamos la linea contable perteneciente a la retencion
        move_line = {
            'name': retention.name or '/',
            'debit': debit,
            'credit': credit,
            'account_id': retention.account_id.id,
            'tax_line_id': retention.retention_id.tax_id.id,
            'journal_id': voucher.journal_id.id,
            'period_id': voucher.period_id.id,
            'partner_id': voucher.partner_id.id,
            'currency_id': company_currency !=
            current_currency and current_currency or False,
            'amount_currency': company_currency !=
            current_currency and sign * retention.amount or 0.0,
            'date': voucher.date,
            'date_maturity': voucher.date_due
        }

        return move_line

    @api.multi
    def apply_retention_sequence(self):
        sequence_model = self.env['ir.sequence']
        for rtl in self:
            number = sequence_model.next_by_code('retention.applied')
            rtl.write({
                'certificate_no': number,
            })


class AccountPaymentOrder(models.Model):
    _name = 'account.payment.order'
    _inherit = 'account.payment.order'

    retention_ids = fields.One2many(comodel_name='retention.tax.line',
                                    inverse_name='payment_order_id',
                                    string='Retentions', readonly=True,
                                    states={'draft': [('readonly', False)]})

    @api.multi
    def get_retentions_amount(self):
        return sum(self.retention_ids.mapped('amount'))

    @api.multi
    def payment_order_amount_hook(self):
        amount = super().payment_order_amount_hook()
        amount += self.get_retentions_amount()
        return amount

    @api.onchange('retention_ids')
    def onchange_retentions(self):
        amount = self.payment_order_amount_hook()
        self.amount = amount

    @api.multi
    def create_move_line_hook(self, move_id, move_lines):
        voucher = self
        move_lines = super(AccountPaymentOrder, self).\
            create_move_line_hook(move_id, move_lines)

        for ret in voucher.retention_ids:
            res = ret.create_voucher_move_line()
            if res:
                res['move_id'] = move_id
                move_lines.append(res)

            # Escribimos valores del voucher en la retention tax line
            ret_vals = {
                'voucher_number': voucher.number,
                'partner_id': voucher.partner_id.id,
            }
            ret.write(ret_vals)

        return move_lines
