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

from openerp import models, fields, api
from openerp.tools.translate import _


class account_voucher(models.Model):
    _name = 'account.voucher'
    _inherit = 'account.voucher'

    issued_check_ids = fields.One2many('account.issued.check', 'voucher_id', 'Issued Checks', readonly=True, required=False, states={'draft': [('readonly', False)]})
    third_check_receipt_ids = fields.One2many('account.third.check', 'source_voucher_id', 'Third Checks', readonly=True, required=False, states={'draft': [('readonly', False)]})
    third_check_ids = fields.Many2many('account.third.check', 'third_check_voucher_rel', 'dest_voucher_id', 'third_check_id', 'Third Checks', readonly=True, states={'draft': [('readonly', False)]})

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
    def _get_issued_checks_amount(self):
        # TODO: testear que este metodo funcione
        # issued_check_obj = self.pool.get('account.issued.check')
        amount = 0.0
        for check in self.issued_check_ids:
            am = check.amount
            if am:
                amount += float(am)

        # for check in self.issued_check_ids:
        #     if check[0] == 4 and check[1] and not check[2]:
        #         # am = issued_check_obj.read(cr, uid, check[1], ['amount'], context=context)['amount']
        #         am = check.amount
        #         if am:
        #             amount += float(am)
        #     if check[2]:
        #         amount += check[2]['amount']
        return amount

    @api.multi
    def _get_third_checks_amount(self):
        # TODO: testear que este metodo funcione
        # third_check_obj = self.pool.get('account.third.check')
        amount = 0.0
        for check in self.third_check_ids:
            am = check.amount
            if am:
                amount += am
        # for check in self.third_check_ids:
        #     if check[0] == 6 and check[2]:
        #         for c in check[2]:
        #             # am = third_check_obj.read(cr, uid, c, ['amount'], context=context)['amount']
        #             am = check.amount
        #             if am:
        #                 amount += float(am)
        return amount

    @api.multi
    def _get_third_checks_receipt_amount(self):
        # TODO: testear que este metodo funcione
        # third_check_obj = self.pool.get('account.third.check')
        amount = 0.0

        for check in self.third_check_receipt_ids:
            am = check.amount
            if am:
                amount += am
        # for check in self.third_check_ids:
        #     if check[0] == 4 and check[1] and not check[2]:
        #         # am = third_check_obj.read(cr, uid, check[1], ['amount'], context=context)['amount']
        #         am = check.amount
        #         if am:
        #             amount += float(am)
        #     if check[2]:
        #         amount += check[2]['amount']

        return amount

    @api.onchange('third_check_receipt_ids')
    def onchange_third_receipt_checks(self):
        amount = self._get_payment_lines_amount()
        amount += self._get_third_checks_receipt_amount()

        self.amount = amount

    @api.onchange('payment_line_ids')
    def onchange_payment_line(self):
        amount = self._get_payment_lines_amount()
        amount += self._get_issued_checks_amount()
        amount += self._get_third_checks_amount()
        amount += self._get_third_checks_receipt_amount()

        self.amount = amount

    @api.onchange('issued_check_ids')
    def onchange_issued_checks(self):
        amount = self._get_payment_lines_amount()
        amount += self._get_issued_checks_amount()
        amount += self._get_third_checks_amount()

        self.amount = amount

    @api.onchange('third_check_ids')
    def onchange_third_checks(self):
        amount = self._get_payment_lines_amount()
        amount += self._get_issued_checks_amount()
        amount += self._get_third_checks_amount()

        self.amount = amount

    @api.multi
    def unlink(self):
        for voucher in self:
            voucher.third_check_ids.unlink()
            voucher.issued_check_ids.unlink()
            super(account_voucher, voucher).unlink()

    @api.multi
    def create_move_line_hook(self, move_id, move_lines):
        move_lines = super(account_voucher, self).create_move_line_hook(move_id, move_lines)

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
                move_lines.append(res)
                vals = {'state': 'issued', 'receiving_partner_id': self.partner_id.id}

                if not check.origin:
                    vals['origin'] = self.reference

                if not check.issue_date:
                    vals['issue_date'] = self.date
                check.write(vals)

        return move_lines

#    def add_precreated_check(self, cr, uid, ids, context=None):
#        third_obj = self.pool.get('account.third.check')
#
#        partner_id = self.read(cr, uid, ids[0], ['partner_id'], context)['partner_id'][0]
#        # Buscamos todos los cheques de terceros del partner del voucher
#        # y que esten en estado 'draft'
#        check_ids = third_obj.search(cr, uid, [('source_partner_id','=',partner_id), ('state','=','draft'),('voucher_id','=',False)], context=context)
#
#        if check_ids:
#            third_obj.write(cr, uid, check_ids, {'voucher_id': ids[0]}, context)
#
#        return True

    @api.multi
    def cancel_voucher(self):
        res = super(account_voucher, self).cancel_voucher()

        for voucher in self:
            # Cancelamos los cheques de tercero en recibos
            third_receipt_checks = voucher.third_check_receipt_ids
            third_receipt_checks.cancel_check()

            # Volvemos a cartera los cheques de tercero en pagos
            third_checks = voucher.third_check_ids
            third_checks.return_wallet()

            # Cancelamos los cheques emitidos
            issued_checks = voucher.issued_check_ids
            issued_checks.cancel_check()

        return res

    @api.multi
    def action_cancel_draft(self):
        res = super(account_voucher, self).action_cancel_draft()
        for voucher in self:
            # A draft los cheques emitidos
            issued_checks = voucher.issued_check_ids
            issued_checks.write({'state': 'draft'})

            # A draft los cheques de tercero en cobros
            third_checks = voucher.third_check_receipt_ids
            third_checks.write({'state': 'draft'})

        return res

account_voucher()
