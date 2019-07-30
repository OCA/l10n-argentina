##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp


class PerceptionTaxLine(models.Model):
    _name = "perception.tax.line"
    _description = "Perception Tax Line"

    # TODO: Tal vaz haya que ponerle estados a este objeto
    # para manejar tambien propiedades segun estados
    name = fields.Char('Perception', required=True, size=64)
    date = fields.Date('Date', index=True)
    invoice_id = fields.Many2one(
        'account.invoice', 'Invoice', ondelete='cascade')
    account_id = fields.Many2one(
        'account.account', string='Tax Account',
        required=True, domain=[
            ('type', '<>', 'view'),
            ('type', '<>', 'income'),
            ('type', '<>', 'closed')])
    base = fields.Float('Base', digits=dp.get_precision('Account'))
    amount = fields.Float('Amount', digits=dp.get_precision('Account'))
    perception_id = fields.Many2one(
        'perception.perception', string='Perception Configuration',
        required=True,
        help="Perception configuration used for this perception tax, " +
        "where all the configuration resides. Accounts, Tax Codes, etc.")
    base_amount = fields.Float(
        'Base Code Amount', digits=dp.get_precision('Account'))
    tax_amount = fields.Float(
        'Tax Code Amount', digits=dp.get_precision('Account'))
    company_id = fields.Many2one(
        related='account_id.company_id', string='Company',
        store=True, readonly=True)
    partner_id = fields.Many2one(
        'res.partner', string='Partner', required=True)
    vat = fields.Char(
        related='partner_id.vat', string='CIF/NIF', readonly=True)
    state_id = fields.Many2one(
        'res.country.state', string="State/Province")
    ait_id = fields.Many2one(
        'account.invoice.tax', string='Invoice Tax', ondelete='cascade')

    @api.onchange('perception_id')
    def onchange_perception(self):
        if not self.perception_id:
            return {}
        self.name = self.perception_id.name
        self.account_id = self.perception_id.tax_id.account_id.id
        self.state_id = self.perception_id.state_id.id
        return None

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
            'analytic': self.perception_id.account_analytic_id.id,
        })

        return taxes


class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    perception_ids = fields.One2many(
        'perception.tax.line', 'invoice_id', string='Perception',
        readonly=True, states={'draft': [('readonly', False)]})

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

    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        """ If not date write the invoice date """
        for p in self.perception_ids:
            if not p.date:
                date = self.date_invoice or fields.Date.context_today(self)
                p.write({'date': date})

        return super().finalize_invoice_move_lines(move_lines)

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
