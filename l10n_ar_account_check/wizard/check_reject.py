# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2008-2011  Thymbra
#    Copyright (c) 2011-2014 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#    All Rights Reserved. See AUTHORS for details.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


# TODO: Que pasa si no se valida la Nota de Debito???

class account_check_reject(osv.osv_memory):
    _name = 'account.check.reject'

    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}

        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company_id = context.get('company_id', user.company_id.id)
        journal_obj = self.pool.get('account.journal')
        domain = [('company_id', '=', company_id)]

        domain.append(('type', '=', 'sale'))
        res = journal_obj.search(cr, uid, domain, limit=1)
        return res and res[0] or False

    _columns = {
        'reject_date': fields.date('Reject Date', required=True),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True),
        'expense_line_ids': fields.one2many('check.reject.expense', 'reject_id', 'Expenses'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
    }

    _defaults = {
        'journal_id': _get_journal,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.invoice', context=c),
    }

#    def _get_address_invoice(self, cr, uid, partner):
#        partner_obj = self.pool.get('res.partner')
#        return partner_obj.address_get(cr, uid, [partner],
#                ['contact', 'invoice'])

    def action_reject(self, cr, uid, ids, context=None):
        check_config_obj = self.pool.get('account.check.config')

        if context is None:
            context = {}

        third_check_obj = self.pool.get('account.third.check')
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')

        wizard = self.browse(cr, uid, ids[0], context=context)
        record_ids = context.get('active_ids', [])
        check_objs = third_check_obj.browse(cr, uid, record_ids, context=context)

        period_id = self.pool.get('account.period').find(cr, uid, wizard.reject_date)[0]

        for check in check_objs:
            if check.state not in ('deposited', 'delivered'):
                raise osv.except_osv(_("Error"), _('Check %s has to be deposited or delivered!') % (check.number))

            partner = check.source_partner_id

            invoice_vals = {
                'origin': 'Check : %s' % check.number,
                'name': 'Debit Note due to rejected check %s [%s]' % (check.number or '', check.source_voucher_id.number),
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

            vals = invoice_obj.onchange_partner_id(cr, uid, ids, 'out_invoice', partner.id, date_invoice=wizard.reject_date, payment_term=partner.property_payment_term, partner_bank_id=False, company_id=wizard.company_id.id, context=context)

            invoice_vals.update(vals['value'])
            lines = []
            # Linea del cheque rechazado

            res = check_config_obj.search(cr, uid, [('company_id', '=', check.company_id.id)])
            if not len(res):
                raise osv.except_osv(_(' ERROR!'), _('There is no check configuration for this Company!'))

            config = check_config_obj.browse(cr, uid, res[0])

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

            vals = invoice_line_obj.product_id_change(cr, uid, [], product=False, uom_id=False, qty=1, name=name, type='out_invoice', partner_id=partner.id, price_unit=check.amount, currency_id=False, context=context, company_id=check.company_id.id)

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

                vals = invoice_line_obj.product_id_change(cr, uid, [], product=expense.product_id.id, uom_id=False, qty=1, name='', type='out_invoice', partner_id=partner.id, price_unit=expense.price, currency_id=False, context=context, company_id=wizard.company_id.id)

                invoice_line_vals.update(vals['value'])
                invoice_line_vals['price_unit'] = expense.price
                taxes = [(6, 0, invoice_line_vals['invoice_line_tax_id'])]
                invoice_line_vals['invoice_line_tax_id'] = taxes
                lines.append((0, 0, invoice_line_vals))

            invoice_vals['invoice_line'] = lines

            invoice_vals['pos_ar_id'] = invoice_vals['pos_ar_id']

            # Creamos la nota de debito
            debit_note_id = invoice_obj.create(cr, uid, invoice_vals)

            # TODO: Chequear que es lo mismo el estado en el que este, asi quitamos
            # este if que parece no tener sentido
            if check.state == 'delivered':
                third_check_obj.reject_check(cr, uid, [check.id], context=context)
            elif check.state == 'deposited':
                third_check_obj.reject_check(cr, uid, [check.id], context=context)

            # Guardamos la referencia a la nota de debito del rechazo
            # TODO: Cambiar el write del state, tiene que ser por workflow.
            third_check_obj.write(cr, uid, check.id, {'debit_note_id': debit_note_id, 'state': 'rejected'}, context=context)

        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'l10n_ar_point_of_sale', 'view_pos_invoice_form')
        form_id = form_res and form_res[1] or False
        tree_res = ir_model_data.get_object_reference(cr, uid, 'l10n_ar_point_of_sale', 'view_pos_invoice_filter')
        tree_id = tree_res and tree_res[1] or False

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


account_check_reject()


class check_reject_expense(osv.osv_memory):
    _name = 'check.reject.expense'

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'reject_id': fields.many2one('account.check.reject', 'Reject'),
        'price': fields.float('Amount', digits_compute=dp.get_precision('Account'), required=True),
    }

check_reject_expense()
