# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError,ValidationError
from odoo.tools import float_is_zero, pycompat
from odoo.addons import decimal_precision as dp
from datetime import date
import os
import base64
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
        _inherit = 'account.move'

        def action_post(self):
            if self.move_type in ['out_invoice','out_refund','in_invoice','in_refund']:
                self.compute_taxes()
            return super(AccountMove, self).action_post()

        def _compute_tax_amounts(self):
            for rec in self:
                if rec.move_tax_ids:
                    if rec.move_type in ['out_invoice','out_refund','in_invoice','in_refund']:
                        vat_taxable_amount = 0
                        other_taxes_amount = 0
                        vat_exempt_base_amount = 0
                        vat_amount = 0
                        for move_tax in rec.move_tax_ids:
                            if move_tax.tax_id.tax_group_id.tax_type == 'vat' and move_tax.tax_id.tax_group_id.l10n_ar_vat_afip_code != '2':
                                vat_taxable_amount += move_tax.base_amount
                                vat_amount += move_tax.tax_amount
                            elif move_tax.tax_id.tax_group_id.l10n_ar_vat_afip_code == '2':
                                vat_exempt_base_amount += move_tax.base_amount
                            else:
                                other_taxes_amount += move_tax.tax_amount
                        rec.vat_taxable_amount = vat_taxable_amount
                        rec.vat_amount = vat_amount
                        rec.other_taxes_amount = other_taxes_amount
                        rec.vat_exempt_base_amount = vat_exempt_base_amount
                        rec.vat_untaxed_base_amount = 0
                    else:
                        rec.vat_taxable_amount = 0
                        rec.vat_amount = 0
                        rec.other_taxes_amount = 0
                        rec.vat_exempt_base_amount = 0
                        rec.vat_untaxed_base_amount = 0
                else:
                   rec.vat_taxable_amount = 0
                   rec.vat_amount = 0
                   rec.other_taxes_amount = 0
                   rec.vat_exempt_base_amount = 0
                   rec.vat_untaxed_base_amount = 0

        def compute_taxes(self):
            self.ensure_one()
            if self.state == 'draft':
                if self.move_type in ['out_invoice','out_refund','in_invoice','in_refund']:
                    for move_tax in self.move_tax_ids:
                        move_tax.unlink()
                    for invoice_line in self.invoice_line_ids:
                        if invoice_line.tax_ids:
                            for tax in invoice_line.tax_ids.ids:
                                account_tax = self.env['account.tax'].browse(tax)
                                move_tax_id = self.env['account.move.tax'].search([('move_id','=',self.id),('tax_id','=',tax)])
                                if account_tax.tax_group_id.tax_type == 'vat':
                                    if not move_tax_id:
                                        vals = {
                                                'move_id': self.id,
                                                'tax_id': tax
                                                }
                                        move_tax_id = self.env['account.move.tax'].create(vals)
                                    move_tax_id.base_amount = move_tax_id.base_amount + invoice_line.price_subtotal
                                    move_tax_id.tax_amount = move_tax_id.tax_amount + invoice_line.price_subtotal * (account_tax.amount / 100)
                    for taxes in self.amount_by_group:
                        in_tax = self.env['account.tax'].search([('tax_group_id', '=', taxes[0])], limit=1)
                        if in_tax.tax_group_id.tax_type != 'vat':
                            move_tax_id = self.env['account.move.tax'].search([('move_id', '=', self.id),('tax_id', '=', in_tax.id)])
                            if not move_tax_id:
                                vals = {
                                    'move_id': self.id,
                                    'tax_id': in_tax.id
                                    }
                                move_tax_id = self.env['account.move.tax'].create(vals)
                            move_tax_id.base_amount = move_tax_id.base_amount + taxes[2]
                            move_tax_id.tax_amount = move_tax_id.tax_amount + taxes[1]

        def recompute_taxes(self):
            self.ensure_one()
            if self.move_type in ['out_invoice','out_refund','in_invoice','in_refund']:
                for move_tax in self.move_tax_ids:
                    move_tax.unlink()
                for invoice_line in self.invoice_line_ids:
                    if invoice_line.tax_ids:
                        for tax in invoice_line.tax_ids.ids:
                            account_tax = self.env['account.tax'].browse(tax)
                            move_tax_id = self.env['account.move.tax'].search([('move_id','=',self.id),('tax_id','=',tax)])
                            if account_tax.tax_group_id.tax_type == 'vat':
                                if not move_tax_id:
                                    vals = {
                                            'move_id': self.id,
                                            'tax_id': tax
                                            }
                                    move_tax_id = self.env['account.move.tax'].create(vals)
                                move_tax_id.base_amount = move_tax_id.base_amount + invoice_line.price_subtotal
                                move_tax_id.tax_amount = move_tax_id.tax_amount + invoice_line.price_subtotal * (account_tax.amount / 100)
                for taxes in self.amount_by_group:
                    in_tax = self.env['account.tax'].search([('tax_group_id', '=', taxes[0])], limit=1)
                    if in_tax.tax_group_id.tax_type != 'vat':
                        move_tax_id = self.env['account.move.tax'].search([('move_id', '=', self.id),('tax_id', '=', in_tax.id)])
                        if not move_tax_id:
                            vals = {
                                'move_id': self.id,
                                'tax_id': in_tax.id
                                }
                            move_tax_id = self.env['account.move.tax'].create(vals)
                        move_tax_id.base_amount = move_tax_id.base_amount + taxes[2]
                        move_tax_id.tax_amount = move_tax_id.tax_amount + taxes[1]

        move_tax_ids = fields.One2many(comodel_name='account.move.tax',inverse_name='move_id',string='Impuestos')
        vat_taxable_amount = fields.Float('Base imponible de IVA',compute=_compute_tax_amounts)
        vat_amount = fields.Float('Monto de IVA',compute=_compute_tax_amounts)
        other_taxes_amount = fields.Float('Monto de Otros Impuestos',compute=_compute_tax_amounts)
        vat_exempt_base_amount = fields.Float('Monto de IVA',compute=_compute_tax_amounts)
        vat_untaxed_base_amount = fields.Float('Monto de IVA no gravado',compute=_compute_tax_amounts)

class AccountMoveTax(models.Model):
        _name = 'account.move.tax'
        _description = 'account.move.tax'

        move_id = fields.Many2one('account.move',string='Account Move')
        tax_id = fields.Many2one('account.tax',string='Tax')
        base_amount = fields.Float('Base Amount')
        tax_amount = fields.Float('Tax Amount')

class AccountTaxGroup(models.Model):
        _inherit = 'account.tax.group'

        tax_type = fields.Selection(selection=[('vat','IVA'),('withholdings','Percepciones/Retenciones'),('exempt','Exentos')],string='Tipo de Impuestos')

