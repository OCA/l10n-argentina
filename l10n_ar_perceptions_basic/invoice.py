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
from openerp import models, fields, api
from openerp.addons import decimal_precision as dp
import time


class perception_tax_line(models.Model):
    _name = "perception.tax.line"
    _description = "Perception Tax Line"

    # TODO: Tal vaz haya que ponerle estados a este objeto para manejar tambien propiedades segun estados
    name = fields.Char('Perception', required=True, size=64)
    date = fields.Date('Date', select=True)
    invoice_id = fields.Many2one('account.invoice', 'Invoice', ondelete='cascade')
    account_id = fields.Many2one('account.account', 'Tax Account', required=True, domain=[('type', '<>', 'view'), ('type', '<>', 'income'), ('type', '<>', 'closed')])
    base = fields.Float('Base', digits_compute=dp.get_precision('Account'))
    amount = fields.Float('Amount', digits_compute=dp.get_precision('Account'))
    perception_id = fields.Many2one('perception.perception', 'Perception Configuration', required=True, help="Perception configuration used for this perception tax, where all the configuration resides. Accounts, Tax Codes, etc.")
    base_code_id = fields.Many2one('account.tax.code', 'Base Code', help="The account basis of the tax declaration.")
    base_amount = fields.Float('Base Code Amount', digits_compute=dp.get_precision('Account'))
    tax_code_id = fields.Many2one('account.tax.code', 'Tax Code', help="The tax basis of the tax declaration.")
    tax_amount = fields.Float('Tax Code Amount', digits_compute=dp.get_precision('Account'))
    company_id = fields.Many2one(related='account_id.company_id', string='Company', store=True, readonly=True)
    partner_id = fields.Many2one(related='invoice_id.partner_id', string='Partner', readonly=True)
    vat = fields.Char(related='invoice_id.partner_id.vat', string='CIF/NIF', readonly=True)
    state_id = fields.Many2one('res.country.state', string="State/Province")
    ait_id = fields.Many2one('account.invoice.tax', 'Invoice Tax', ondelete='cascade')

    @api.onchange('perception_id')
    def onchange_perception(self):
        if not self.perception_id:
            return {}
        self.name = self.perception_id.name
        self.account_id = self.perception_id.tax_id.account_collected_id.id
        self.base_code_id = self.perception_id.tax_id.base_code_id.id
        self.tax_code_id = self.perception_id.tax_id.tax_code_id.id
        self.state_id = self.perception_id.state_id.id
        return None

    @api.v8
    def _compute(self, invoice, base, amount):
        """
        self: perception.tax.line
        invoice: account.invoice
        """
        tax = self.perception_id.tax_id
        # Nos fijamos la currency de la invoice
        currency = invoice.currency_id.with_context(date=invoice.date_invoice or fields.Date.context_today(invoice))
        company_currency = invoice.company_id.currency_id

        if invoice.type in ('out_invoice', 'in_invoice'):
            base_amount = currency.compute(base * tax.base_sign, company_currency, round=False)
            tax_amount = currency.compute(amount * tax.tax_sign, company_currency, round=False)
        else:  # invoice is Refund
            base_amount = currency.compute(base * tax.ref_base_sign, company_currency, round=False)
            tax_amount = currency.compute(amount * tax.ref_tax_sign, company_currency, round=False)
        return (tax_amount, base_amount)

perception_tax_line()


class account_invoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    perception_ids = fields.One2many('perception.tax.line', 'invoice_id', string='Perception', readonly=True, states={'draft': [('readonly', False)]})

    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        """finalize_invoice_move_lines(invoice, move_lines) -> move_lines
        Hook method to be overridden in additional modules to verify and possibly alter the
        move lines to be created by an invoice, for special cases.
        :param self: browsable record of the invoice that is generating the move lines
        :param move_lines: list of dictionaries with the account.move.lines (as for create())
        :return: the (possibly updated) final move_lines to create for this invoice
        """
        # Como nos faltan los account.move.line de las bases imponibles de las percepciones
        # utilizamos este hook para agregarlos
        company_currency = self.company_id.currency_id.id
        current_currency = self.currency_id.id

        for p in self.perception_ids:
            sign = p.perception_id.tax_id.base_sign
            tax_amount, base_amount = p._compute(self, p.base, p.amount)

            # ...y ahora creamos la linea contable perteneciente a la base imponible de la perception
            # Notar que credit & debit son 0.0 ambas. Lo que cuenta es el tax_code_id y el tax_amount
            move_line = {
                'name': p.name + '(Base Imp)',
                'ref': self.internal_number or False,
                'debit': 0.0,
                'credit': 0.0,
                'account_id': p.account_id.id,
                'tax_code_id': p.base_code_id.id,
                'tax_amount': base_amount,
                'journal_id': self.journal_id.id,
                'period_id': self.period_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': company_currency != current_currency and sign * p.amount or 0.0,
                'date': self.date_invoice or time.strftime('%Y-%m-%d'),
                'date_maturity': self.date_due or False,
            }

            # Si no tenemos seteada la fecha, escribimos la misma que la de la factura
            if not p.date:
                p.write({'date': move_line['date']})

            move_lines.insert(len(move_lines) - 1, (0, 0, move_line))
        return move_lines

account_invoice()


class account_invoice_tax(models.Model):
    _name = "account.invoice.tax"
    _inherit = "account.invoice.tax"

    # Aca le agregamos las account_invoice_taxes pertenecientes a las Percepciones
    @api.v8
    def hook_compute_invoice_taxes(self, invoice, tax_grouped):
        # Si se hacen calculo automatico de Percepciones,
        # esta funcion ya no tiene sentido
        # Esta key se setea en el modulo l10n_ar_perceptions
        auto = self.env.context.get('auto', False)

        if auto:
            return super(account_invoice_tax, self).hook_compute_invoice_taxes(invoice, tax_grouped)

        currency = invoice.currency_id.with_context(date=invoice.date_invoice or fields.Date.context_today(invoice))

        # Recorremos las percepciones y las computamos como account.invoice.tax
        for line in invoice.perception_ids:
            val = {}
            tax = line.perception_id.tax_id
            val['invoice_id'] = invoice.id
            val['name'] = line.name
            val['amount'] = line.amount
            val['manual'] = False
            val['sequence'] = 10
            val['is_exempt'] = False
            val['base'] = line.base
            val['tax_id'] = tax.id

            # Computamos tax_amount y base_amount
            tax_amount, base_amount = line._compute(invoice, val['base'], val['amount'])

            if invoice.type in ('out_invoice', 'in_invoice'):
                val['base_code_id'] = line.base_code_id.id
                val['tax_code_id'] = line.tax_code_id.id
                val['base_amount'] = base_amount
                val['tax_amount'] = tax_amount
                val['account_id'] = tax.account_collected_id.id
                val['account_analytic_id'] = tax.account_analytic_collected_id.id
            else:
                val['base_code_id'] = tax.ref_base_code_id.id
                val['tax_code_id'] = tax.ref_tax_code_id.id
                val['base_amount'] = base_amount
                val['tax_amount'] = tax_amount
                val['account_id'] = tax.account_paid_id.id
                val['account_analytic_id'] = tax.account_analytic_paid_id.id

            key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
            if not key in tax_grouped:
                tax_grouped[key] = val
            else:
                tax_grouped[key]['amount'] += val['amount']
                tax_grouped[key]['base'] += val['base']
                tax_grouped[key]['base_amount'] += val['base_amount']
                tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = currency.round(t['base'])
            t['amount'] = currency.round(t['amount'])
            t['base_amount'] = currency.round(t['base_amount'])
            t['tax_amount'] = currency.round(t['tax_amount'])

        return super(account_invoice_tax, self).hook_compute_invoice_taxes(invoice, tax_grouped)

account_invoice_tax()
