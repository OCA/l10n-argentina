##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import models, fields, api


class AccountJournal(models.Model):
    _name = "account.journal"
    _inherit = "account.journal"

    code = fields.Char(
        string='Code', size=8, required=True,
        help="The code will be displayed on reports.")
    type = fields.Selection(selection=[
        ('sale_refund', 'Sale Refund'),
        ('purchase_refund', 'Purchase Refund'),
        ('purchase', 'Purchase'),
        ('receipt', 'Receipts'),
        ('sale', 'Sale'),
        ('cash', 'Cash'),
        ('general', 'General'),
        ('bank', 'Bank and Checks'),
        ('situation', 'Opening/Closing Situation'),
        ('payment', 'Payment')], string='Type', size=32, required=True,
        help="Select 'Sale' for customer invoices journals.\n\
              Select 'Purchase' for supplier invoices journals.\n\
              Select 'Cash' or 'Bank' for journals that are \
              used in customer or supplier payments.\n\
              Select 'General' for miscellaneous operations journals.\n\
              Select 'Opening/Closing Situation' for \
              entries generated for new fiscal years.\n\
              Select 'Receipt' for Receipt Vouchers.\n\
              Select 'Payment' for Payment Vouchers.")
    priority = fields.Integer()

    @api.model
    def create_sequence(self, vals):
        """
        Create new no_gap entry sequence for every new Joural
        """

        # Creacion de secuencia. Si es de tipo payment o receipt
        # la secuencia la armamos de otra manera
        journal_type = vals['type']

        if journal_type not in ['receipt', 'payment']:
            return super().create_sequence(vals)

        # in account.journal code is actually the prefix of the sequence
        # whereas ir.sequence code is a key to lookup global sequences.
        prefix = vals['code'].upper()

        seq = {
            'name': vals['name'],
            'implementation': 'no_gap',
            'prefix': prefix + '-',
            'padding': 8,
            'number_increment': 1
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        sequence = self.env['ir.sequence'].create(seq)
        return sequence.id
