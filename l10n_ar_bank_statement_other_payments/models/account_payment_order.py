##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import api, models


class AccountPaymentOrder(models.Model):

    _inherit = 'account.payment.order'

    @api.multi
    def proforma_voucher(self):
        ret = super(AccountPaymentOrder, self).proforma_voucher()

        for payment_order in self:
            for concept in payment_order.concept_line_ids:
                journal = concept.journal_id or payment_order.journal_id
                if not journal.detach_statement_lines():
                    continue

                self.create_statement_line(concept, journal)

        return ret


class AccountPaymentOrderConceptLine(models.Model):

    _inherit = 'account.payment.order.concept.line'

    def _prepare_statement_line_data(self):
        payment_order = self.payment_order_id
        line_type = payment_order.type

        # Si el voucher no tiene partner, ponemos el de la compania
        partner = payment_order.partner_id or \
            payment_order.company_id.partner_id
        journal = self.journal_id or payment_order.journal_id

        if payment_order.type == 'payment':
            sign = 1
        else:
            sign = -1

        amount = self.amount * sign

        st_line_data = {
            'ref': self.name,
            'name': self.name or payment_order.number,
            'account_id': self.account_id.id,
            'journal_id': journal.id,
            'date': payment_order.date,
            'company_id': payment_order.company_id.id,
            'payment_order_id': payment_order.id,
            'partner_id': partner.id,
            'line_type': line_type,
            'amount': amount,
            'state': 'open',
        }

        return st_line_data
