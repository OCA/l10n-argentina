##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import models, api, fields


class CloseAccountJournalWizard(models.TransientModel):
    _name = 'close.account.journal.wizard'

    period_id = fields.Many2one(
        comodel_name="date.period",
        string='Period',
        required=True)
    closed = fields.Boolean(compute='_compute_closed')

    @api.multi
    def button_open(self):
        active_ids = self.env.context.get('active_ids')
        account_journal_id = self.env['account.journal'].browse(active_ids)
        self.period_id.write({
            'journal_ids': [(3, account_journal_id.id, 0)],
        })

    @api.multi
    def button_close(self):
        active_ids = self.env.context.get('active_ids')
        account_journal_id = self.env['account.journal'].browse(active_ids)
        self.period_id.write({
            'journal_ids': [(4, account_journal_id.id, 0)],
        })

    @api.depends('period_id')
    def _compute_closed(self):
        active_ids = self.env.context.get('active_ids')
        account_journal_id = self.env['account.journal'].browse(active_ids)
        if account_journal_id in self.period_id.journal_ids:
            self.closed = True
        else:
            self.closed = False
