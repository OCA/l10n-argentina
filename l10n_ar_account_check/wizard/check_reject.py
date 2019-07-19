###############################################################################
#   Copyright (C) 2008-2011  Thymbra
#   Copyright (c) 2012-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from datetime import datetime

from odoo import models, fields, _, api
from odoo.exceptions import ValidationError
import odoo.addons.decimal_precision as dp


class AccountCheckReject(models.Model):
    _name = 'account.check.reject'

    @api.model
    def _get_journal(self):
        user = self.env.user
        company_id = self.env.context.get('company_id', user.company_id.id)
        journal_obj = self.env['account.journal']
        domain = [('company_id', '=', company_id)]

        domain.append(('type', '=', 'sale'))
        res = journal_obj.search(domain, limit=1)
        return res and res.id or False

    reject_date = fields.Date(string='Reject Date', required=True)
    journal_id = fields.Many2one(
        comodel_name='account.journal', string='Journal',
        required=True, default=_get_journal)
    expense_line_ids = fields.One2many(
        comodel_name='check.reject.expense', inverse_name='reject_id',
        string='Expenses')
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'account.invoice'))

    @api.multi
    def action_reject(self):
        check_config_obj = self.env['account.check.config']
        third_check_obj = self.env['account.third.check']
        invoice_obj = self.env['account.invoice']

        wizard = self
        record_ids = self.env.context.get('active_ids', [])
        check_objs = third_check_obj.browse(record_ids)

        for check in check_objs:

            check.reject_date = wizard.reject_date

            partner = check.source_partner_id

            config = check_config_obj.search(
                [('company_id', '=', check.company_id.id)])
            if not config:
                raise ValidationError(_(' ERROR! There is no check \
                    configuration for this Company!'))

            inv_account_id = config.receivable_rejected_account_id
            if not inv_account_id:
                inv_account_id = partner.property_account_receivable_id

            invoice_vals = {
                'origin': _('Check : %s') % check.number,
                'name': _('Debit Note due to rejected check %s [%s]') %
                (check.number or '', check.source_payment_order_id.number),
                'type': 'out_invoice',
                'is_debit_note': True,
                'account_id': inv_account_id.id,
                'partner_id': partner.id,
                'journal_id': wizard.journal_id.id,
                'fiscal_position': partner.property_account_position_id.id,
                'company_id': wizard.company_id.id,
            }

            lines = []
            # Linea del cheque rechazado

            account_id = False
            if check.state == 'delivered':
                account_id = config.rejected_account_id.id
            elif check.state == 'deposited':
                account_id = check.deposit_bank_id.account_id.id
            elif check.state == 'wallet':
                account_id = config.account_id.id

            name = _('Check Rejected') + ' ' + check.number + ' '
            name += datetime.strptime(
                wizard.reject_date, '%Y-%m-%d').strftime('%d/%m/%Y')
            invoice_line_vals = {
                'name': name,
                'quantity': 1,
                'price_unit': check.amount,
                'account_id': account_id,
            }

            lines.append((0, 0, invoice_line_vals))

            # Lineas de gastos
            for expense in wizard.expense_line_ids:

                product = expense.product_id
                account_id = product.property_account_expense_id
                if not account_id:
                    account_id = product.categ_id.\
                        property_account_expense_categ_id
                if not account_id:
                    raise ValidationError(
                        _('Please, fill the expense account in the product.'))

                invoice_line_vals = {
                    'name': expense.product_id.name,
                    'product_id': expense.product_id.id,
                    'quantity': 1,
                    'price_unit': expense.price,
                    'account_id': account_id.id,
                    'invoice_line_tax_ids': [
                        (6, 0, expense.product_id.taxes_id.ids)],
                }

                lines.append((0, 0, invoice_line_vals))

            invoice_vals['invoice_line_ids'] = lines

            # Creamos la nota de debito
            debit_note_id = invoice_obj.create(invoice_vals)

            debit_note_id._onchange_partner_id()

            # Volvemos a cambiar la cuenta que sobreescribio el onchange
            debit_note_id.account_id = inv_account_id

            debit_note_id._onchange_invoice_line_ids()

        # TODO: Chequear que es lo mismo el estado en el que este,
        # asi quitamos este if que parece no tener sentido
        if check.state == 'delivered' or check.state == 'deposited':
            check.reject_check()

        # Guardamos la referencia a la nota de debito del rechazo
        check.state = 'rejected'
        check.debit_note_id = debit_note_id

        form_res = self.env.ref('l10n_ar_point_of_sale.view_pos_invoice_form')
        form_id = form_res and form_res.id or False
        tree_res = self.env.ref(
            'l10n_ar_point_of_sale.view_pos_invoice_filter')  # ????
        tree_id = tree_res and tree_res.id or False

        return {
            'name': _('Invoice'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'account.invoice',
            'res_id': debit_note_id.id,
            'view_id': False,
            'views': [(form_id, 'form'), (tree_id, 'tree')],
            'type': 'ir.actions.act_window',
        }


class CheckRejectExpense(models.Model):
    _name = 'check.reject.expense'

    product_id = fields.Many2one(
        comodel_name='product.product', string='Product', required=True)
    reject_id = fields.Many2one(
        comodel_name='account.check.reject', string='Reject')
    price = fields.Float(
        string='Amount', digits=dp.get_precision('Account'), required=True)


class CheckRejectIssuedCheck(models.Model):
    _name = 'check.reject.issued.check'

    reject_date = fields.Date(string='Reject Date', required=True)
    note = fields.Text(string='Note')

    def action_reject(self):
        issued_check_obj = self.env['account.issued.check']
        record_ids = self.env.context.get('active_ids', [])

        check_objs = issued_check_obj.browse(record_ids)
        for check in check_objs:
            check.write({'reject_date': self.reject_date, 'note': self.note})
            check.reject_check()

        return {'type': 'ir.actions.act_window_close'}
