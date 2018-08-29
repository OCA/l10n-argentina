###############################################################################
#   Copyright (C) 2008-2011  Thymbra
#   Copyright (c) 2012-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from odoo import models, fields, _, api
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp


# TODO: Que pasa si no se valida la Nota de Debito???

# TODO !!!! This class is not properly migrated at all
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
    journal_id = fields.Many2one(comodel_name='account.journal',
                                 string='Journal', required=True,
                                 default=_get_journal)
    expense_line_ids = fields.One2many(comodel_name='check.reject.expense',
                                       inverse_name='reject_id',
                                       string='Expenses')
    company_id = fields.Many2one(comodel_name='res.company', string='Company',
                                 required=True,
                                 default=lambda self: self.env['res.company'].
                                 _company_default_get('account.invoice'))


#    def _get_address_invoice(self, cr, uid, partner):
#        partner_obj = self.pool.get('res.partner')
#        return partner_obj.address_get(cr, uid, [partner],
#                ['contact', 'invoice'])

    @api.multi
    def action_reject(self):
        check_config_obj = self.env['account.check.config']
        third_check_obj = self.env['account.third.check']
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']

        wizard = self
        record_ids = self.env.context.get('active_ids', [])
        check_objs = third_check_obj.browse(record_ids)

        period_id = self.env['account.period'].find(wizard.reject_date)[0]

        for check in check_objs:
            if check.state not in ('deposited', 'delivered'):
                raise UserError(_("Error! Check %s has to be deposited \
                    or delivered!") % (check.number))

            partner = check.source_partner_id

            invoice_vals = {
                'origin': 'Check : %s' % check.number,
                'name': 'Debit Note due to rejected check %s [%s]' %
                (check.number or '', check.source_payment_order_id.number),
                'type': 'out_invoice',
                'is_debit_note': True,
                'account_id': partner.property_account_receivable.id,
                'partner_id': partner.id,
                'date_invoice': wizard.reject_date,
                'period_id': period_id,
                'journal_id': wizard.journal_id.id,
                'fiscal_position': partner.property_account_position.id,
                'company_id': wizard.company_id.id,
            }

            vals = invoice_obj.onchange_partner_id(
                'out_invoice', partner.id, date_invoice=wizard.reject_date,
                payment_term=partner.property_payment_term,
                partner_bank_id=False, company_id=wizard.company_id.id)

            invoice_vals.update(vals['value'])
            lines = []
            # Linea del cheque rechazado

            config = check_config_obj.search(
                [('company_id', '=', check.company_id.id)])
            if not config:
                raise UserError(_(' ERROR! There is no check \
                    configuration for this Company!'))

            account_id = False
            if check.state == 'delivered':
                account_id = config.account_id.id
            elif check.state == 'deposited':
                account_id = check.deposit_bank_id.account_id.id

            name = 'Check Rejected' + check.number
            invoice_line_vals = {
                'name': name,
                'quantity': 1,
            }

            vals = invoice_line_obj.product_id_change(
                product=False, uom_id=False, qty=1, name=name,
                type='out_invoice', partner_id=partner.id,
                price_unit=check.amount, currency_id=False,
                company_id=check.company_id.id)

            invoice_line_vals.update(vals['value'])
            invoice_line_vals['price_unit'] = check.amount
            invoice_line_vals['account_id'] = account_id
            lines.append((0, 0, invoice_line_vals))

            # Lineas de gastos
            for expense in wizard.expense_line_ids:
                invoice_line_vals = {
                    'product_id': expense.product_id.id,
                    'quantity': 1,
                }

                vals = invoice_line_obj.product_id_change(
                    product=expense.product_id.id, uom_id=False, qty=1,
                    name='', type='out_invoice', partner_id=partner.id,
                    price_unit=expense.price, currency_id=False,
                    company_id=wizard.company_id.id)

                invoice_line_vals.update(vals['value'])
                invoice_line_vals['price_unit'] = expense.price
                taxes = [(6, 0, invoice_line_vals['invoice_line_tax_id'])]
                invoice_line_vals['invoice_line_tax_id'] = taxes
                lines.append((0, 0, invoice_line_vals))

            invoice_vals['invoice_line'] = lines

            invoice_vals['pos_ar_id'] = invoice_vals['pos_ar_id']

            # Creamos la nota de debito
            debit_note_id = invoice_obj.create(invoice_vals)

            # TODO: Chequear que es lo mismo el estado en el que este,
            # asi quitamos este if que parece no tener sentido
            if check.state == 'delivered':
                third_check_obj.reject_check([check.id])
            elif check.state == 'deposited':
                third_check_obj.reject_check([check.id])

            # Guardamos la referencia a la nota de debito del rechazo
            # TODO: Cambiar el write del state, tiene que ser por workflow.
            check.write({'debit_note_id': debit_note_id, 'state': 'rejected'})

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
            'res_id': debit_note_id,
            'view_id': False,
            'views': [(form_id, 'form'), (tree_id, 'tree')],
            'context': {'type': 'out_invoice', 'is_debit_note': True},
            'type': 'ir.actions.act_window',
        }


class CheckRejectExpense(models.Model):
    _name = 'check.reject.expense'

    product_id = fields.Many2one(comodel_name='product.product',
                                 string='Product', required=True)
    reject_id = fields.Many2one(comodel_name='account.check.reject',
                                string='Reject')
    price = fields.Float(string='Amount',
                         digits=dp.get_precision('Account'),
                         required=True)


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
