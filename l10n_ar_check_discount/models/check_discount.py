###############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (Julian Corso)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CheckDiscount(models.Model):
    _name = 'check.discount'
    _description = 'Discounts checks'

    name = fields.Char(string="Name", default=_('New'))
    state = fields.Selection([
        ('draft', _('Draft')),
        ('discounted', _('Discounted')),
        ('cancel', _('Cancel')),
        ], string='Status', readonly=True,
        copy=False, index=True,
        track_visibility='onchange', default='draft')
    journal_id = fields.Many2one(
        'account.journal', string='Reception Journal')
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Receptor Bank")
    invoice_number = fields.Char(
        string="Invoice Number")
    expense_invoice_date = fields.Date(
        string="Expense Invoice Date")
    expense_invoice_accounting_date = fields.Date(
        string="Expense Invoice Accounting Date")
    check_ids = fields.Many2many(
        'account.third.check',
        relation='third_check_discount_rel',
        column1='check_discount_id', column2='account_third_check_id',
        string='Checks')
    check_discount_line_ids = fields.One2many(
        'check.discount.line',
        inverse_name='check_discount_id',
        string='Concepts')
    discount_date = fields.Date(string="Discount Date")
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda s: s.get_default_currency())
    amount_checks = fields.Monetary(
        string='T. Checks',
        compute='_compute_amount_checks', store=True)
    amount_concepts = fields.Monetary(
        string='T. Concepts',
        compute='_compute_amount_concepts', store=True)
    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amount_total', store=True)
    allowed_product_ids = fields.Many2many(
        comodel_name='product.product',
        relation='check_discount_product_ids_rel',
        column1='check_discount_id', column2='product_id',
        string="Allowed products")
    expense_invoice_id = fields.Many2one(
        comodel_name='account.invoice',
        string="Expense Invoice")
    note = fields.Text(
        string='Note')

    @api.model
    def create(self, vals):
        seq = self.env['ir.sequence'].next_by_code('seq.check.disc') or '/-/'
        vals['name'] = seq
        return super().create(vals)

    @api.model
    def get_default_currency(self):
        return self.env.user.company_id.currency_id

    @api.depends('check_ids')
    def _compute_amount_checks(self):
        for disc in self:
            disc.amount_checks = sum(disc.check_ids.mapped('amount'))

    @api.depends('check_discount_line_ids')
    def _compute_amount_concepts(self):
        for disc in self:
            disc.amount_concepts = sum(
                disc.check_discount_line_ids.mapped('amount'))

    @api.depends('amount_checks', 'amount_concepts')
    def _compute_amount_total(self):
        for disc in self:
            disc.amount_total = disc.amount_checks - disc.amount_concepts

    @api.multi
    def action_discount(self):
        self.ensure_one()
        if not self.journal_id:
            raise ValidationError(
                _("A Journal must be set!"))
        if not self.check_ids:
            raise ValidationError(
                _("Some Checks must be loaded!"))
        self._discount_checks()
        if self.check_discount_line_ids:
            invoice = self._generate_expense_invoice()
            invoice.action_invoice_open()
            self.expense_invoice_id = invoice
        # TODO
        # move = self._generate_check_discount_move()
        # self.accredit_move_id = move
        return self.write({
            'state': 'discounted',
        })

    @api.multi
    def _generate_expense_invoice(self):
        invoice_model = self.env['account.invoice']
        invoice_vals = self._prepare_expense_invoice_vals()
        invoice = invoice_model.new(invoice_vals)
        default_vals = invoice.default_get(invoice._fields)
        [setattr(invoice, fname, val)
         for fname, val in default_vals.items()]
        invoice._onchange_partner_id()
        inv_vals = invoice._convert_to_write({
            fname: getattr(invoice, fname) for fname in invoice._cache
        })
        inv_vals.update(invoice_vals)
        invoice = invoice_model.create(inv_vals)
        return invoice

    @api.multi
    def _prepare_expense_invoice_vals(self):
        line_vals = []
        for expense_line in self.check_discount_line_ids:
            lv = expense_line._prepare_expense_invoice_line_vals()
            line_vals.append(lv)
        vals = {
            'internal_number': self.invoice_number,
            'date_invoice': self.expense_invoice_date,
            'date': self.expense_invoice_accounting_date,
            'name': self.name,
            'partner_id': self.partner_id.id,
            'type': 'in_invoice',
            'currency_id': self.currency_id.id,
            'invoice_line_ids': [(0, False, l) for l in line_vals],
        }
        return vals

    @api.multi
    def _discount_checks(self):
        for check in self.check_ids:
            check.state = 'discounted'
            check.discount_date = self.discount_date or \
                fields.Date.context_today(self)
        return True

    @api.multi
    def action_cancel(self):
        for check in self.check_ids:
            check.state = 'wallet'
            check.discount_date = False
        if self.expense_invoice_id:
            self.expense_invoice_id.unlink()
        return self.write({
            'state': 'cancel',
        })

    @api.multi
    def action_back_to_draft(self):
        return self.write({
            'state': 'draft',
        })

    @api.multi
    def action_view_invoice(self):
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        action['views'] = [(self.env.ref('account.invoice_supplier_form').id,
                            'form')]
        action['res_id'] = self.expense_invoice_id.id
        return action


class CheckDiscountLine(models.Model):
    _name = 'check.discount.line'
    _description = 'Discounts checks Line'

    check_discount_id = fields.Many2one(
        'check.discount', string='Check Discount',
        required=True, ondelete="cascade")
    product_id = fields.Many2one(
        'product.product', string='Concept')
    account_id = fields.Many2one(
        'account.account', string="Account")
    currency_id = fields.Many2one(
        'res.currency', related="check_discount_id.currency_id")
    amount_untaxed = fields.Monetary(
        string='Amount Untaxed')
    tax_id = fields.Many2one(
        'account.tax', string='Tax')
    amount = fields.Monetary(
        string='Amount',
        compute="_compute_amount")

    @api.onchange('product_id')
    def onchange_product_id(self):
        for line in self:
            line.account_id = line.product_id.property_account_expense_id

    @api.depends('amount_untaxed', 'tax_id')
    def _compute_amount(self):
        for rec in self:
            tax_vals = rec.tax_id.compute_all(
                rec.amount_untaxed, rec.currency_id, 1, rec.product_id)
            rec.amount = tax_vals.get('total_included')

    @api.multi
    def _prepare_expense_invoice_line_vals(self):
        self.ensure_one()
        expense_line = self
        lv = {
            'name': expense_line.product_id.partner_ref,
            'product_id': expense_line.product_id.id,
            'account_id': expense_line.account_id.id,
            'quantity': 1,
            'invoice_line_tax_ids': [(6, 0, expense_line.tax_id.ids)],
            'price_unit': expense_line.amount_untaxed,
        }
        return lv
