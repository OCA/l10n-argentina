##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import models, api, fields


class DatePeriod(models.Model):
    _inherit = 'date.period'

    period_state = fields.Selection([
        ('open', 'Open'),
        ('partial', 'Partialy Closed'),
        ('closed', 'Closed'),
        ], string='Status', readonly=True,
        copy=False, compute="_compute_period_state",
        track_visibility='onchange', default='open', store=True)

    journal_ids = fields.Many2many(
        comodel_name='account.journal', relation='date_period_journal_rel',
        column1='close_period_id', column2='journal_id', string='Journals')

    @api.depends('journal_ids')
    def _compute_period_state(self):
        journal_model = self.env['account.journal']
        for rec in self:
            if len(rec.journal_ids) == journal_model.search_count([]):
                rec.period_state = 'closed'
            elif rec.journal_ids:
                rec.period_state = 'partial'
            else:
                rec.period_state = 'open'
