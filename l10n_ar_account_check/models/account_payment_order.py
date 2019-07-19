##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountPaymentOrder(models.Model):
    _name = 'account.payment.order'
    _inherit = 'account.payment.order'

    issued_check_ids = fields.One2many(
        comodel_name='account.issued.check',
        inverse_name='payment_order_id',
        string='Issued Checks',
        readonly=True, required=False,
        states={'draft': [('readonly', False)]})
    third_check_receipt_ids = fields.One2many(
        comodel_name='account.third.check',
        inverse_name='source_payment_order_id',
        string='Third Checks',
        readonly=True, required=False,
        states={'draft': [('readonly', False)]})
    third_check_ids = fields.Many2many(
       comodel_name='account.third.check',
       relation='third_check_voucher_rel',
       column1='dest_payment_order_id',
       column2='third_check_id',
       string='Third Checks', readonly=True,
       states={'draft': [('readonly', False)]})

    @api.multi
    def _amount_checks(self):
        self.ensure_one()
        res = {}
        res['issued_check_amount'] = 0.00
        res['third_check_amount'] = 0.00
        res['third_check_receipt_amount'] = 0.00
        if self.issued_check_ids:
            for issued_check in self.issued_check_ids:
                res['issued_check_amount'] += issued_check.amount
        if self.third_check_ids:
            for third_check in self.third_check_ids:
                res['third_check_amount'] += third_check.amount
        if self.third_check_receipt_ids:
            for third_rec_check in self.third_check_receipt_ids:
                res['third_check_receipt_amount'] += third_rec_check.amount
        return res

    @api.multi
    def get_issued_checks_amount(self):
        return sum(self.issued_check_ids.mapped('amount'))

    @api.multi
    def get_third_checks_amount(self):
        return sum(self.third_check_ids.mapped('amount'))

    @api.multi
    def get_third_check_receipts_amount(self):
        return sum(self.third_check_receipt_ids.mapped('amount'))

    @api.onchange(
        'third_check_ids',
        'issued_check_ids',
        'third_check_receipt_ids')
    def onchange_checks(self):
        amount = self.payment_order_amount_hook()
        self.amount = amount

    @api.multi
    def payment_order_amount_hook(self):
        amount = super().payment_order_amount_hook()
        amount += self.get_issued_checks_amount()
        amount += self.get_third_checks_amount()
        amount += self.get_third_check_receipts_amount()
        return amount

    @api.multi
    def unlink(self):
        for voucher in self:
            if voucher.type == 'receipt':
                voucher.third_check_ids.unlink()
            voucher.issued_check_ids.unlink()
            super(AccountPaymentOrder, voucher).unlink()

    @api.multi
    def create_move_line_hook(self, move_id, move_lines):
        move_lines = super(AccountPaymentOrder, self).\
            create_move_line_hook(move_id, move_lines)

        if self.type in ('sale', 'receipt'):
            for check in self.third_check_receipt_ids:
                if check.amount == 0.0:
                    continue

                res = check.create_voucher_move_line(self)
                res['move_id'] = move_id
                move_lines.append(res)
                check.to_wallet()

        elif self.type in ('purchase', 'payment'):
            # Cheques recibidos de terceros que los damos a un proveedor
            for check in self.third_check_ids:
                if check.amount == 0.0:
                    continue

                res = check.create_voucher_move_line(self)
                res['move_id'] = move_id
                move_lines.append(res)
                check.check_delivered()

            # Cheques propios que los damos a un proveedor
            for check in self.issued_check_ids:
                if check.amount == 0.0:
                    continue

                res = check.create_voucher_move_line()
                res['move_id'] = move_id
                res['issued_check_id'] = check.id
                move_lines.append(res)

                if check.type == 'postdated':
                    state = 'waiting'
                else:
                    state = 'issued'

                vals = {
                    'state': state,
                    'payment_move_id': move_id,
                    'receiving_partner_id': self.partner_id.id
                }

                if not check.origin:
                    vals['origin'] = self.reference

                if not check.issue_date:
                    vals['issue_date'] = self.date
                check.write(vals)

        return move_lines

    @api.multi
    def cancel_voucher(self):
        res = super(AccountPaymentOrder, self).cancel_voucher()

        for voucher in self:
            # Cancelamos los cheques de tercero en recibos
            third_receipt_checks = voucher.third_check_receipt_ids
            third_receipt_checks.cancel_check()

            # Volvemos a cartera los cheques de tercero en pagos
            third_checks = voucher.third_check_ids
            third_checks.return_wallet()

            # Cancelamos los cheques emitidos
            issued_checks = voucher.issued_check_ids
            for check in issued_checks:
                if check.type == 'postdated' and check.accredited:
                    err = _('Check number %s is postdated and has \
                        already been accredited!\nPlease break the \
                        conciliation of that check first.') % check.number
                    raise ValidationError(err)

            issued_checks.cancel_check()

        return res

    @api.multi
    def action_cancel_draft(self):
        res = super(AccountPaymentOrder, self).action_cancel_draft()
        for voucher in self:
            # A draft los cheques emitidos
            issued_checks = voucher.issued_check_ids
            issued_checks.write({'state': 'draft'})

            # A draft los cheques de tercero en cobros
            third_checks = voucher.third_check_receipt_ids
            third_checks.write({'state': 'draft'})

        return res
