# -*- coding: utf-8 -*-
###############################################################################
#   Copyright (c) 2019 Eynes/E-mips (Julian Corso)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals):
        period_model = self.env['date.period']
        period_date = fields.Datetime.context_timestamp(
            self, datetime.strptime(vals['date'], '%Y-%m-%d'))
        period = period_model._get_period(period_date)
        if vals['journal_id'] in period.journal_ids.ids:
            raise ValidationError(
                _("Can't create an account move on a closed period."))
        return super(AccountMove, self).create(vals)

    @api.multi
    def write(self, vals):
        if self.journal_id.id in self.period_id.journal_ids.ids:
            raise ValidationError(
                _("Can't edit an account move on a closed period."))
        period_model = self.env['date.period']
        date = vals.get('date')
        if not date:
            date = self.date
        if not date:
            return super(AccountMove, self).write(vals)
        period_date = fields.Datetime.context_timestamp(
            self, datetime.strptime(date, '%Y-%m-%d'))
        period = period_model._get_period(period_date)
        journal_id = vals.get('journal_id')
        if not journal_id:
            journal_id = self.journal_id
        if isinstance(journal_id, self.env['account.journal'].__class__):
            journal_id = journal_id.id
        if journal_id in period.journal_ids.ids:
            raise ValidationError(
                _("Can't edit an account move to a closed period."))
        return super(AccountMove, self).write(vals)

    @api.multi
    def unlink(self):
        if self.journal_id.id in self.period_id.journal_ids.ids:
            raise ValidationError(
                _("Can't delete an account move on a closed period."))
        return super(AccountMove, self).unlink()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def create(self, vals):
        move_model = self.env['account.move']
        move_id = move_model.browse(vals['move_id'])
        period_model = self.env['date.period']
        period_date = fields.Datetime.context_timestamp(
            self, datetime.strptime(move_id.date, '%Y-%m-%d'))
        period = period_model._get_period(period_date)
        if move_id.journal_id.id in period.journal_ids.ids:
            raise ValidationError(
                _("Can't create an account move line on a closed period."))
        return super(AccountMoveLine, self).create(vals)

    @api.multi
    def write(self, vals):
        bypass_fields = ['reconciled', 'full_reconcile_id']
        if any(key not in bypass_fields for key in list(vals.keys())):
            for rec in self:
                if rec.move_id.journal_id.id in \
                        rec.move_id.period_id.journal_ids.ids:
                    raise ValidationError(
                        _("Can't edit an account move line on a closed period."))
        return super(AccountMoveLine, self).write(vals)

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.move_id.journal_id.id in \
                    rec.move_id.period_id.journal_ids.ids:
                raise ValidationError(
                    _("Can't delete an account move line on a closed period."))
        return super(AccountMoveLine, self).unlink()
