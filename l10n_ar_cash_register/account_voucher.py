# -*- coding: utf-8 -*-
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

from openerp.osv import osv, fields
from openerp.tools.translate import _

class account_voucher(osv.osv):

    _name = "account.voucher"
    _inherit = "account.voucher"

    _columns = {
        'statement_bank_line_ids': fields.one2many('account.bank.statement.line', 'ref_voucher_id', string='Bank statement lines'),
    }

    def proforma_voucher(self, cr, uid, ids, context=None):
        super(account_voucher, self).proforma_voucher(cr, uid, ids, context=context)
        invoice_obj = self.pool.get("account.invoice")

        for vou in self.browse(cr, uid, ids, context=context):
            if vou.type in 'receipt':
                sign = 1
                aux_account = vou.partner_id.property_account_receivable.id
            if vou.type in 'payment':
                sign = -1
                aux_account = vou.partner_id.property_account_payable.id

            invoice_ids = set()
            for dr_line in vou.line_dr_ids:
                invoice_ids.add(dr_line.invoice_id.id)

            invoices = invoice_obj.browse(cr, uid, list(invoice_ids), context=context)
            invoices_ref = ", ".join(name or '' for __, name in invoices.name_get())

            for line in vou.payment_line_ids:
                if line.payment_mode_id.type in 'cash':
                    voucher_number = line.voucher_id.number

                    amount = line.amount * sign

                    voucher_date = line.voucher_id.date or fields.date.context_today(self,cr,uid,context=context)
                    statement = self.pool.get('account.bank.statement').search(cr, uid,
                    [('journal_id','=', line.payment_mode_id.id),('state','=','open'),
                     ('date', '<=', voucher_date)], order='date desc')

                    if statement:
                        # Elegimos la primer caja que sera la que corresponde en fecha
                        st_line = {
                            'name': voucher_number,
                            'date': line.date or vou.date,
                            'amount': amount,
                            'account_id': aux_account,
                            'state': 'conciliated',
                            'type': vou.type,
                            # Si el voucher no tiene partner, ponemos el de la compania
                            'partner_id': line.voucher_id.partner_id and
                                            line.voucher_id.partner_id.id or
                                            line.voucher_id.company_id.partner_id.id,
                            'company_id': vou.company_id.id,
                            'ref_voucher_id': vou.id,
                            'creation_type': 'system',
                            'statement_id': statement[0],
                            'ref': invoices_ref,
                            'journal_id': line.payment_mode_id.id,
                        }

                        st_id = self.pool.get('account.bank.statement.line').create(cr, uid, st_line, context)
                    else:
                        raise osv.except_osv(_("Validate Error!"), _("Cannot validate a voucher with cash and box not open."))
            return True

    def cancel_voucher(self, cr, uid, ids, context=None):

        statement_line_obj = self.pool.get('account.bank.statement.line')

        for voucher in self.browse(cr, uid, ids, context=None):
            for statement_line in voucher.statement_bank_line_ids:
                statement_line_obj.unlink(cr, uid, statement_line.id, context=None)
        return super(account_voucher, self).cancel_voucher(cr, uid, ids, context=None)

account_voucher()
