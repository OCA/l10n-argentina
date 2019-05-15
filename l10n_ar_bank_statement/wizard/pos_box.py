##############################################################################
#
#    Copyright (C) 2004-2010 Pexego Sistemas Informáticos. All Rights Reserved
#    Copyright (C) 2010-2014 Eynes - Ingeniería del software All Rights Reserved
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models
from odoo.addons.account.wizard.pos_box import CashBox as CashBoxOdoo
from odoo.addons.account.wizard.pos_box import CashBoxIn as CashBoxInOdoo
from odoo.addons.account.wizard.pos_box import CashBoxOut as CashBoxOutOdoo

@api.multi
def get_account(self, record=None):
    """ Provides hook to set an account on cash.box movements """
    res = self.concept_id.account_id
    fallback = record.journal_id.company_id.transfer_account_id
    if not res and not fallback:
        raise exceptions.ValidationError(_('Cannot found account to do the transfer'))
    return res or fallback

class CashBoxIn(models.TransientModel):
    _inherit = 'cash.box.in'

    name = fields.Text(
        string="name",
        required=True,
    )
    concept_id = fields.Many2one(
        'pos.box.concept',
        string='concept',
        required=True,
        ondelete='cascade',
    )

    get_account = api.multi(get_account)

    # Disabled to force users to set a proper reason
    @api.onchange("concept_id")
    def onchange_concept_id(self):
        pass

    @api.model_cr
    def _register_hook(self):
        res = super()._register_hook()
        CashBoxInOdoo._patch_method(
            '_calculate_values_for_statement_line',
            _calculate_values_for_statement_line_cashboxin
        )

    @api.multi
    def _calculate_values_for_statement_line(self, record):
        vals = super(CashBoxIn, self)._calculate_values_for_statement_line(record)
        vals["concept_id"] = self.concept_id.id
        vals["line_type"] = "in"
        vals["state"] = "confirm"
        return vals


class CashBoxOut(models.TransientModel):
    _inherit = 'cash.box.out'

    name = fields.Text(
        string="Name",
        required=True,
    )
    concept_id = fields.Many2one(
        'pos.box.concept',
        string='Concept',
        required=True,
        ondelete='cascade',
    )

    get_account = api.multi(get_account)

    # Disabled to force users to set a proper reason
    @api.onchange("concept_id")
    def onchange_concept_id(self):
        pass

    @api.model_cr
    def _register_hook(self):
        res = super()._register_hook()
        CashBoxOutOdoo._patch_method(
            '_calculate_values_for_statement_line',
            _calculate_values_for_statement_line_cashboxout
        )


    @api.multi
    def _calculate_values_for_statement_line(self, record):
        vals = super(CashBoxOut, self)._calculate_values_for_statement_line(record)
        vals["concept_id"] = self.concept_id.id
        vals["line_type"] = "out"
        vals["state"] = "confirm"
        return vals


@api.multi
def _calculate_values_for_statement_line_cashboxin(self, record):
    account_id = self.get_account(record).id
    return {
        'date': record.date,
        'statement_id': record.id,
        'journal_id': record.journal_id.id,
        'amount': self.amount or 0.0,
        'account_id': account_id,
        'ref': '%s' % (self.ref or ''),
        'name': self.name,
    }

@api.multi
def _calculate_values_for_statement_line_cashboxout(self, record):
    amount = self.amount or 0.0
    account_id = self.get_account(record).id
    return {
        'date': record.date,
        'statement_id': record.id,
        'journal_id': record.journal_id.id,
        'amount': -amount if amount > 0.0 else amount,
        'account_id': account_id,
        'name': self.name,
    }
