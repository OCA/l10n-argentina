###############################################################################
#   Copyright (c) 2011-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp


class perception_tax_line(models.Model):
    _name = "perception.tax.line"
    _description = "Perception Tax Line"

    # @api.v8
    # def _compute(self, invoice, base, amount):
    #     """
    #     self: perception.tax.line
    #     invoice: account.invoice
    #     """
    #     tax = self.perception_id.tax_id
    #     # Nos fijamos la currency de la invoice
    #     currency = invoice.currency_id.with_context(
    #         date=invoice.date_invoice or fields.Date.context_today(invoice))
    #     company_currency = invoice.company_id.currency_id

    #     if invoice.type in ('out_invoice', 'in_invoice'):
    #         base_amount = currency.compute(
    #             base, company_currency, round=False)
    #             # base * tax.base_sign, company_currency, round=False) # noqa
    #         tax_amount = currency.compute(
    #             amount, company_currency, round=False)
    #             # amount * tax.tax_sign, company_currency, round=False) # noqa
    #     else:  # invoice is out_refund
    #         base_amount = currency.compute(
    #             base, company_currency, round=False)
    #             # base * tax.ref_base_sign, company_currency, round=False) # noqa
    #         tax_amount = currency.compute(
    #             amount, company_currency, round=False)
    #             # amount * tax.ref_tax_sign, company_currency, round=False) # noqa
    #     return (tax_amount, base_amount)

    @api.multi
    def compute_all(self, currency=None):
        if len(self) == 0:
            company_id = self.env.user.company_id
        else:
            company_id = self[0].company_id
        if not currency:
            currency = company_id.currency_id
        taxes = []
        taxes.append({
            'id': self.perception_id.tax_id.id,
            'name': self.name,
            'amount': self.amount,
            'base': self.base,
            'account_id': self.account_id.id,
            # 'refund_account_id': ,
            'analytic': self.perception_id.account_analytic_id.id,
            # 'price_include': .
        })

        return taxes

    # TODO: Tal vaz haya que ponerle estados a este objeto
    # para manejar tambien propiedades segun estados
    name = fields.Char('Perception', required=True, size=64)
    date = fields.Date('Date', index=True)
    invoice_id = fields.Many2one('account.invoice', 'Invoice',
                                 ondelete='cascade')
    account_id = fields.Many2one('account.account',
                                 string='Tax Account',
                                 required=True,
                                 domain=[('type', '<>', 'view'),
                                         ('type', '<>', 'income'),
                                         ('type', '<>', 'closed')])
    base = fields.Float('Base', digits=dp.get_precision('Account'))
    amount = fields.Float('Amount', digits=dp.get_precision('Account'))
    perception_id = fields.Many2one('perception.perception',
                                    string='Perception Configuration',
                                    required=True,
                                    help="Perception configuration \
                                    used for this perception tax, \
                                    where all the configuration resides. \
                                    Accounts, Tax Codes, etc.")
    base_code_id = fields.Many2one(
        'account.tax.code', 'Base Code',
        help="The account basis of the tax declaration.")
    base_amount = fields.Float('Base Code Amount',
                               digits=dp.get_precision('Account'))
    tax_code_id = fields.Many2one('account.tax.code',
                                  string='Tax Code',
                                  help="The tax basis of the tax declaration.")
    tax_amount = fields.Float('Tax Code Amount',
                              digits=dp.get_precision('Account'))
    company_id = fields.Many2one(related='account_id.company_id',
                                 string='Company', store=True,
                                 readonly=True)
    partner_id = fields.Many2one('res.partner',
                                 string='Partner',
                                 required=True)
    vat = fields.Char(related='partner_id.vat',
                      string='CIF/NIF',
                      readonly=True)
    state_id = fields.Many2one('res.country.state',
                               string="State/Province")
    ait_id = fields.Many2one('account.invoice.tax',
                             string='Invoice Tax',
                             ondelete='cascade')

    @api.onchange('perception_id')
    def onchange_perception(self):
        if not self.perception_id:
            return {}
        self.name = self.perception_id.name
        self.account_id = self.perception_id.tax_id.account_id.id
        # self.base_code_id = self.perception_id.tax_id.base_code_id.id
        # self.tax_code_id = self.perception_id.tax_id.tax_code_id.id
        self.state_id = self.perception_id.state_id.id
        return None


class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    perception_ids = fields.One2many('perception.tax.line', 'invoice_id',
                                     string='Perception', readonly=True,
                                     states={'draft': [('readonly', False)]})

    # Done
    @api.multi
    def onchange_partner_id(self):
        """
        If partner changes set the partner_id for existent perceptions
        """
        res = super(AccountInvoice, self).onchange_partner_id()

        perception_ids = self.perception_ids.ids
        if self.partner_id and perception_ids:
            upd_lst = []
            for p in perception_ids:
                upd_lst.append((1, p, {'partner_id': self.partner_id}))
            res['value']['perception_ids'] = upd_lst
        return res

    # @api.multi
    # def finalize_invoice_move_lines(self, move_lines):
    #     """finalize_invoice_move_lines(invoice, move_lines) -> move_lines
    #     Hook method to be overridden in additional modules to verify and
    #     possibly alter the move lines to be created by an invoice, for
    #     special cases.
    #     :param self: browsable record of the
    #      invoice that is generating the move lines
    #     :param move_lines: list of dictionaries with
    #      the account.move.lines (as for create())
    #     :return: the (possibly updated) final
    #      move_lines to create for this invoice
    #     """
    #     # Como nos faltan los account.move.line de
    #     # las bases imponibles de las percepciones
    #     # utilizamos este hook para agregarlos
    #     company_currency = self.company_id.currency_id.id
    #     current_currency = self.currency_id.id

    #     for p in self.perception_ids:
    #         # sign = p.perception_id.tax_id.base_sign
    #         tax_amount, base_amount = p._compute(self, p.base, p.amount)

    #         # ...y ahora creamos la linea contable perteneciente
    #         # a la base imponible de la perception
    #         # Notar que credit & debit son 0.0 ambas. Lo
    #         # que cuenta es el tax_code_id y el tax_amount
    #         move_line = {
    #             'name': p.name + '(Base Imp)',
    #             'ref': self.internal_number or False,
    #             'debit': 0.0,
    #             'credit': 0.0,
    #             'account_id': p.account_id.id,
    #             # 'tax_code_id': p.base_code_id.id,
    #             # 'tax_amount': base_amount,
    #             'journal_id': self.journal_id.id,
    #             'period_id': self.period_id.id,
    #             'partner_id': self.partner_id.id,
    #             'currency_id': company_currency !=
    #             current_currency and current_currency or False,
    #             # 'amount_currency': company_currency !=
    #             # current_currency and sign * p.amount or 0.0,
    #             'amount_currency': company_currency !=
    #             current_currency and p.amount or 0.0,
    #             'date': self.date_invoice or time.strftime('%Y-%m-%d'),
    #             'date_maturity': self.date_due or False,
    #         }

    #         # Si no tenemos seteada la fecha,
    #         # escribimos la misma que la de la factura
    #         if not p.date:
    #             p.write({'date': move_line['date']})

    #         move_lines.insert(len(move_lines) - 1, (0, 0, move_line))
    #     return super(AccountInvoice, self).\
    #         finalize_invoice_move_lines(move_lines)

    def prepare_perception_tax_line_vals(self, tax):
        """ Prepare values to create an perception.tax.line

        Tax parameter is the output of perception.tax.line.compute_all().
        """
        vals = {
            'invoice_id': self.id,
            'name': tax['name'],
            'tax_id': tax['id'],
            'amount': tax['amount'],
            'base': tax['base'],
            'manual': False,
            'sequence': 10,
            'is_exempt': False,
            'account_analytic_id': tax['analytic'],
            'account_id': tax['account_id'],
        }
        return vals

    @api.onchange('perception_ids')
    def onchange_perception_ids(self):
        tax_line_model = self.env['account.invoice.tax']
        for invoice in self:
            tax_ids = []
            tax_grouped = invoice.get_taxes_values()
            for key, tax_val in tax_grouped.items():
                tax_val.pop('invoice_id')
                tax_ids.append(tax_line_model.create(tax_val).id)
            invoice.tax_line_ids = [(6, 0, tax_ids)]

    @api.multi
    def get_taxes_values(self):
        tax_grouped = super(AccountInvoice, self).get_taxes_values()
        for perception in self.perception_ids:
            taxes = perception.compute_all(self.currency_id)
            for tax in taxes:
                val = self.prepare_perception_tax_line_vals(tax)
                key = self.env['account.tax'].browse(
                    tax['id']).get_grouping_key(val)

                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
        return tax_grouped
