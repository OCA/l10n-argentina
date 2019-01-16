# -*- coding: utf-8 -*-
###############################################################################
#   Copyright (c) 2019 Eynes/E-mips (Julian Corso)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging

from odoo import models, api, fields, _, exceptions
# from odoo.exceptions import except_orm
# from odoo.addons.decimal_precision import decimal_precision as dp
# from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, \
#         DEFAULT_SERVER_DATETIME_FORMAT, float_compare


_logger = logging.getLogger(__name__)


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
        self.period_id.write({'journal_ids':[(3, account_journal_id.id, 0)]})

    @api.multi
    def button_close(self):
        active_ids = self.env.context.get('active_ids')
        account_journal_id = self.env['account.journal'].browse(active_ids)
        self.period_id.write({'journal_ids':[(4, account_journal_id.id, 0)]})

    @api.depends('period_id')
    def _compute_closed(self):
        active_ids = self.env.context.get('active_ids')
        account_journal_id = self.env['account.journal'].browse(active_ids)
        if account_journal_id in self.period_id.journal_ids:
            self.closed = True
        else:
            self.closed = False
