###############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (Julian Corso)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging

from odoo import _, api, fields, models

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
        'account.journal', string='Journal',
        required=True)
    check_ids = fields.Many2many(
        'account.third.check',
        relation='third_check_discount_rel',
        string='Checks')
    check_discount_line_ids = fields.One2many(
        'check.discount.line',
        inverse_name='check_discount_id',
        string='Concepts')
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
        for check in self.check_ids:
            check.state = 'discounted'
            check.discount_date = fields.Date.context_today(self)
        return self.write({
            'state': 'discounted',
        })

    @api.multi
    def action_cancel(self):
        for check in self.check_ids:
            check.state = 'wallet'
            check.discount_date = False
        return self.write({
            'state': 'cancel',
        })

    @api.multi
    def action_back_to_draft(self):
        return self.write({
            'state': 'draft',
        })


class CheckDiscountLine(models.Model):
    _name = 'check.discount.line'
    _description = 'Discounts checks Line'

    check_discount_id = fields.Many2one(
        'check.discount', string='Check Discount',
        required=True, ondelete="cascade")
    product_id = fields.Many2one(
        'product.product', string='Concept')
    currency_id = fields.Many2one(
        'res.currency', related="check_discount_id.currency_id")
    amount_untaxed = fields.Monetary(
        string='Amount Untaxed')
    tax_id = fields.Many2one(
        'account.tax', string='Tax')
    amount = fields.Monetary(
        string='Amount',
        compute="_compute_amount")

    @api.depends('amount_untaxed', 'tax_id')
    def _compute_amount(self):
        for rec in self:
            tax_vals = rec.tax_id.compute_all(
                rec.amount_untaxed, rec.currency_id, 1, rec.product_id)
            rec.amount = tax_vals.get('total_included')


class AccountThirdCheck(models.Model):
    _name = 'account.third.check'
    _inherit = 'account.third.check'

    state = fields.Selection(
        selection_add=[('discounted', _('Discounted'))])
    discount_date = fields.Date(
        string='Discount Date')
