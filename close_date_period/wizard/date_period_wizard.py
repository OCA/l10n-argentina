##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import models, api, fields


class CloseDatePeriodWizard(models.TransientModel):
    _name = 'close.date.period.wizard'

    journal_ids = fields.Many2many(
        comodel_name='account.journal',
        relation='close_period_journal_rel',
        column1='close_period_id', column2='journal_id',
        string='Journals')
    closed_journal_ids = fields.Many2many(
        comodel_name='account.journal',
        relation='already_closed_period_journal_rel',
        column1='close_period_id', column2='journal_id',
        default=lambda s: s._get_default_closed_journals(),
        string='Journals')

    @api.multi
    def button_close(self):
        active_ids = self.env.context.get('active_ids')
        date_period_id = self.env['date.period'].browse(active_ids)
        self.journal_ids += self.closed_journal_ids
        date_period_id.write({
            'journal_ids': [(6, 0, self.journal_ids.ids)],
        })

    @api.model
    def _get_default_closed_journals(self):
        active_ids = self.env.context.get('active_ids')
        date_period_id = self.env['date.period'].browse(active_ids)
        return date_period_id.journal_ids.ids


class ReopenDatePeriodWizard(models.TransientModel):
    _name = 'reopen.date.period.wizard'

    journal_ids = fields.Many2many(
        comodel_name='account.journal',
        relation='reopen_period_journal_rel',
        column1='reopen_period_id', column2='journal_id',
        string='Journals')
    closed_journal_ids = fields.Many2many(
        comodel_name='account.journal',
        relation='reopen_already_closed_period_journal_rel',
        column1='reopen_period_id', column2='journal_id',
        default=lambda s: s._get_default_closed_journals(),
        string='Journals')

    @api.multi
    def button_reopen(self):
        active_ids = self.env.context.get('active_ids')
        date_period_id = self.env['date.period'].browse(active_ids)
        for _id in self.journal_ids.ids:
            date_period_id.write({
                'journal_ids': [(3, _id, 0)],
            })

    @api.model
    def _get_default_closed_journals(self):
        active_ids = self.env.context.get('active_ids')
        date_period_id = self.env['date.period'].browse(active_ids)
        return date_period_id.journal_ids.ids
