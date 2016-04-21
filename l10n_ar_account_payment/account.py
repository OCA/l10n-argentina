# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2015 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2015 Eynes (http://www.eynes.com.ar)
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

from openerp import models, fields, api, _


class account_journal(models.Model):
    _name = "account.journal"
    _inherit = "account.journal"

    # Aumentamos el size del code para poder hacer OP 0001, por ejemplo.
    code = fields.Char('Code', size=8, required=True, help="The code will be displayed on reports.")
    type = fields.Selection([('sale', 'Sale'),('sale_refund','Sale Refund'),
                             ('purchase', 'Purchase'), ('purchase_refund','Purchase Refund'),
                             ('cash', 'Cash'), ('bank', 'Bank and Checks'),
                             ('general', 'General'), ('situation', 'Opening/Closing Situation'),
                             ('receipt', 'Receipts'), ('payment', 'Payment')], 'Type', size=32, required=True,
                             help="Select 'Sale' for customer invoices journals."\
                                  " Select 'Purchase' for supplier invoices journals."\
                                  " Select 'Cash' or 'Bank' for journals that are used in customer or supplier payments."\
                                  " Select 'General' for miscellaneous operations journals."\
                                  " Select 'Opening/Closing Situation' for entries generated for new fiscal years."\
                                  " Select 'Receipt' for Receipt Vouchers."\
                                  " Select 'Payment' for Payment Vouchers.")
    priority = fields.Integer()


    @api.model
    def create_sequence(self, vals):
        """ Create new no_gap entry sequence for every new Joural
        """

        # Creacion de secuencia. Si es de tipo payment o receipt
        # la secuencia la armamos de otra manera
        journal_type = vals['type']

        if journal_type not in ['receipt', 'payment']:
            return super(account_journal, self).\
                    create_sequence(vals)

        # in account.journal code is actually the prefix of the sequence
        # whereas ir.sequence code is a key to lookup global sequences.
        prefix = vals['code'].upper()

        seq = {
            'name': vals['name'],
            'implementation':'no_gap',
            'prefix': prefix + '-',
            'padding': 8,
            'number_increment': 1
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        sequence = self.env['ir.sequence'].create(seq)
        return sequence.id


account_journal()
