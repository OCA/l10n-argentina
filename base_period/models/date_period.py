###############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (Cardozo Nicolás Joaquin)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class DatePeriod(models.Model):
    _name = 'date.period'

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", size=7, required=True)
    date_from = fields.Date(string="Start Date", required=True)
    date_to = fields.Date(string="End Date", required=True)
    invoice_ids = fields.One2many(comodel_name="account.invoice",
                                  inverse_name="period_id",
                                  string="Invoice")
    move_ids = fields.One2many(comodel_name="account.move",
                               inverse_name="period_id",
                               string="Move")
    move_line_ids = fields.One2many(comodel_name="account.move.line",
                                    inverse_name="period_id",
                                    string="Move Line")
    inventory_ids = fields.One2many(comodel_name="stock.inventory",
                                    inverse_name="period_id",
                                    string="Stock Inventory")

    @api.multi
    def unlink(self):
        affected_models = [
            'account.move',
            'account.invoice',
            'stock.inventory',
        ]
        affected_models = self._hook_affected_models(affected_models)
        self._check_affected_models(affected_models)
        super().unlink()

    @api.multi
    def _hook_affected_models(self, affected_models):
        return affected_models

    @api.multi
    def _check_affected_models(self, affected_models):
        for record in self:
            search_dict = {}
            for model in affected_models:
                searched = self.env[model].search([
                    ('period_id', '=', self.id)])
                if searched:
                    search_dict[model] = searched
            if search_dict:
                raise ValidationError(
                    _("Error\n You can not unlink a period with " +
                      "associates records.\n Found this ones:\n%s\n" +
                      " For the period %s [ %s ]. ") %
                    (("\n").join(
                        [repr(x.sorted()) for x in search_dict.values()]),
                     record.name, record))

    @api.multi
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('code', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)

        return recs.name_get()

    def create_period(self, p_date):
        for i in range(1, 13):
            new_p_date = p_date + relativedelta(month=i)
            period = str(new_p_date.month) + '/' + str(new_p_date.year)
            period_obj = self.search([('code', 'like', period)])
            if not period_obj:
                first_day = new_p_date + relativedelta(day=1)
                last_day = new_p_date + relativedelta(
                    day=1, months=+1, days=-1)

                args = {
                    'name': period,
                    'code': period,
                    'date_from': first_day,
                    'date_to': last_day,
                }

                self.create(args)

    def _get_period(self, period_date):
        period = str(period_date.month) + '/' + str(period_date.year)
        period_obj = self.search([('code', 'like', period)])
        if not period_obj:
            self.create_period(period_date)
            period = self.search([('code', 'like', period)])
        return period_obj
