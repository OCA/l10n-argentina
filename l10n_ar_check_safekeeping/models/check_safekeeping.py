# -*- coding: utf-8 -*-
###############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (Julian Corso)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging

from odoo import models, api, fields, _, exceptions
# from odoo.exceptions import except_orm
# from odoo.addons.decimal_precision import decimal_precision as dp
# from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, \
#         DEFAULT_SERVER_DATETIME_FORMAT, float_compare


_logger = logging.getLogger(__name__)


class AccountCheckSafekeepingLot(models.Model):
    _name = 'account.check.safekeeping.lot'
    _description = 'check safekeeping'

    name = fields.Char(string="Name", default=_('New'))
    state = fields.Selection([
        ('new', _('New')),
        ('safekeeped', _('Safekeeped')),
        ('done', _('Done')),
        ], string='Status', readonly=True,
        copy=False, index=True,
        track_visibility='onchange', default='new',
        compute='_compute_state', store=True)
    check_ids = fields.One2many('account.third.check',
                                 inverse_name='safekeeping_lot_id',
                                 string=_('Checks'))
    safekeep_date = fields.Date(string='Safekeep Date')
    note = fields.Text(string=_('Note'))

    @api.model
    def create(self, vals):
        seq = self.env['ir.sequence'].next_by_code('seq.check.safekeeping') or '/-/'
        vals['name'] = seq
        return super().create(vals)

    @api.depends('check_ids', 'check_ids.state')
    def _compute_state(self):
        if self.check_ids.filtered(lambda s: s.state == 'safekeeped').ids != []:
            self.state = 'safekeeped'
        elif self.check_ids == self.check_ids.filtered(lambda s: s.state == 'deposited'):
            self.state = 'done'
        else:
            self.state = 'new'

    @api.multi
    def action_safekeep(self):
        self.safekeep_date = fields.Date.context_today(self)
        self.check_ids.action_safekeep()

class AccountThirdCheck(models.Model):
    _name = 'account.third.check'
    _inherit = 'account.third.check'

    state = fields.Selection(selection_add=[('safekeeped', _('Safekeeped'))])
    safekeep_date = fields.Date(string='Safekeep Date')
    safekeeping_lot_id = fields.Many2one('account.check.safekeeping.lot', string=_('Safekeeping Lot'))

    @api.multi
    def action_safekeep(self):
        self.state = 'safekeeped'
        self.safekeep_date = fields.Date.context_today(self)

    @api.multi
    def move_to_safekeeped(self):
        if self.filtered(lambda s: s.safekeeping_lot_id.ids == []) and not self.filtered(lambda s: s.safekeeping_lot_id.ids != []):
            __import__('ipdb').set_trace()
        elif not self.filtered(lambda s: s.safekeeping_lot_id.ids == []) and self.filtered(lambda s: s.safekeeping_lot_id.ids != []):
            for check in self:
                if check.state == 'wallet':
                    check.action_safekeep()
        else:
            raise exceptions.ValidationError(_('Incompatible checks.'))
