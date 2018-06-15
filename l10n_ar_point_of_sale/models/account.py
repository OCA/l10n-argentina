###############################################################################
#   Copyright (c) 2017-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountTax(models.Model):
    _name = "account.tax"
    _inherit = "account.tax"
    _description = "Tax"

    other_group = fields.Char(string='Other Group', size=64)
    is_exempt = fields.Boolean(
        string='Exempt',
        default=False,
        help="Check this if this Tax represent Tax Exempts")
    tax_group = fields.Selection([('vat', 'VAT'),
                                  ('perception', 'Perception'),
                                  ('retention', 'Retention'),
                                  ('internal', 'Internal Tax'),
                                  ('other', 'Other')], string='Tax Group',
                                 default='vat', required=True,
                                 help="This is tax categorization.")


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    # DONE
    # Heredamos para que no ponga el nombre del internal_number
    # al asiento contable, sino que siempre siga la secuencia
    @api.multi
    def post(self):
        invoice = self._context.get('invoice', False)
        self._post_validate()

        for move in self:
            if move.name == '/':
                new_name = False
                journal = move.journal_id
                if journal.sequence_id:
                    # If invoice is actually refund and journal has a
                    # refund_sequence then use that one or use the regular one
                    sequence = journal.sequence_id
                    refund_list = ['out_refund', 'in_refund']
                    if invoice and invoice.type in \
                            refund_list and journal.refund_sequence:
                        if not journal.refund_sequence_id:
                            raise UserError(_('Please define a sequence \
                                for the credit notes'))
                        sequence = journal.refund_sequence_id
                    new_name = sequence.with_context(
                        ir_sequence_date=move.date).next_by_id()
                else:
                    raise UserError(
                        _('Please define a sequence on the journal.'))

                if new_name:
                    move.name = new_name

        return self.write({'state': 'posted'})
