##############################################################################
#
#    Copyright (C) 2010-2014 Eynes - Ingeniería del software All Rights Reserved
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#    All Rights Reserved. See AUTHORS for details.
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models


class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    bank_statement_line_ids = fields.One2many(
        'account.bank.statement.line',
        'payment_order_id',
        string='Bank Statement Lines',
    )
    statement_count = fields.Integer(
        string='Related Bank Statement Qty.',
        compute='_calc_bank_statement_count',
    )

    def _calc_bank_statement_count_from_lines(self, bank_lines):
        return self.env["account.payment"]._calc_bank_statement_count_from_lines(bank_lines)

    @api.depends("bank_statement_line_ids")
    def _calc_bank_statement_count(self):
        for payment in self:
            statement_count = self._calc_bank_statement_count_from_lines(
                payment.bank_statement_line_ids,
            )
            payment.statement_count = statement_count

    @api.multi
    def proforma_voucher(self):
        ret = super(AccountPaymentOrder, self).proforma_voucher()
        bank_st_line_obj = self.env['account.bank.statement.line']

        for payment_order in self:
            for line in payment_order.payment_mode_line_ids:
                journal = line.payment_mode_id or payment_order.journal_id
                if journal.type != 'bank':
                    continue

                st_line_data = line._prepare_statement_line_data()
                bank_st_line_obj.create(st_line_data)

            #for issued_check in vou.issued_check_ids:
            #    if issued_check.type in 'common':
            #        aux_payment_date = issued_check.issue_date
            #    else:
            #        aux_payment_date = issued_check.payment_date

            #    ref_number = issued_check.number
            #    if ref_number:
            #        reference = _('Check No. ') + ref_number
            #    else:
            #        reference = _('Checkbook No. ') + issued_check.checkbook_id.name

            #    st_line = {
            #        'name': reference,
            #        'issue_date': issued_check.issue_date,
            #        'payment_date': aux_payment_date,
            #        'amount': issued_check.amount*-1,
            #        'account_id': vou.partner_id.property_account_payable.id,
            #        'ref': vou.number,
            #        'state': 'draft',
            #        'type': 'payment',
            #        'partner_id': vou.partner_id and vou.partner_id.id,
            #        'ref_voucher_id': vou.id,
            #        'creation_type': 'system',
            #        'ref': vou.reference,
            #        'journal_id': issued_check.account_bank_id.journal_id.id,
            #    }

            #    st_id = bank_st_line_obj.create(st_line)

        return ret

    def check_confirmed_stament_lines(self):
        lines = self.mapped("bank_statement_line_ids")
        return self.env["account.payment"].check_confirmed_stament_lines(lines)

    @api.multi
    def cancel_voucher(self):
        for payment_order in self:
            # Do not proceed if there are confirmed account.bank.statement.line
            if not payment_order.check_confirmed_stament_lines():
                return False

        ret = super(AccountPaymentOrder, self).cancel_voucher()

        # Remove account.bank.statement.line after cancel
        self.mapped("bank_statement_line_ids").unlink()

        return ret

    @api.multi
    def button_open_bank_statements(self):
        bank_lines = self.mapped("bank_statement_line_ids")
        statements = self.env["account.payment"]._get_statements_from_lines(bank_lines)
        form = self.env.ref('account.view_bank_statement_form')
        if len(statements) == 1:
            return {
                'res_model': 'account.bank.statement',
                'src_model': 'account.bank.statement',
                'type': 'ir.actions.act_window',
                'views': [(form.id, 'form')],
                'view_id': form.id,
                'target': 'current',
                'res_id': statements.id,
                'context': str(self.env.context),
            }

        tree = self.env.ref('account.view_bank_statement_tree')
        return {
            'res_model': 'account.bank.statement',
            'src_model': 'account.bank.statement',
            'type': 'ir.actions.act_window',
            'views': [(tree.id, 'tree'), (form.id, 'form')],
            'view_id': False,
            'target': 'current',
            'res_id': statements.ids,
            'context': str(self.env.context),
        }


class AccountPaymentModeLine(models.Model):
    _inherit = 'account.payment.mode.line'

    def _build_invoices_info(self):
        """Show invoices name concatenated."""

        invoices = self.mapped("payment_order_id").mapped("line_ids").mapped("invoice_id")
        return ', '.join(name or '' for _id, name in invoices.name_get())

    def _prepare_statement_line_data(self):
        payment_order = self.payment_order_id
        line_type = payment_order.type

        # Si el voucher no tiene partner, ponemos el de la compania
        partner = payment_order.partner_id or payment_order.company_id.partner_id
        journal = self.payment_mode_id or payment_order.journal_id

        if payment_order.type == 'payment':
            sign = -1
            account = journal.default_debit_account_id
        else:
            sign = 1
            account = journal.default_credit_account_id

        amount = self.amount * sign
        invoices_info = self._build_invoices_info()

        st_line_data = {
            'ref': invoices_info,
            'name': self.name or payment_order.number,
            'date': self.date or payment_order.date,
            'journal_id': journal.id,
            'company_id': payment_order.company_id.id,
            'payment_order_id': payment_order.id,
            'partner_id': partner.id,
            'account_id': account.id,
            'line_type': line_type,
            'amount': amount,
            'state': 'open',
            #'creation_type': 'system',
        }

        return st_line_data
