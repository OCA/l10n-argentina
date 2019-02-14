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
from odoo.addons.account.wizard.pos_box import CashBox


# Disabled to force users to set a proper reason
@api.onchange("concept_id")
def onchange_concept_id(self):
    pass
    # self.name = self.concept_id.name


#_original_run = CashBox._run
#
#
#@api.multi
#def _run(self, records):
#    filtered_records = records.filtered(lambda r: r.journal_id.company_id.transfer_account_id)
#    ret = _original_run(self, filtered_records)
#    for box in self:
#        for record in records - filtered_records:
#            box._create_bank_statement_line(record)
#
#    return ret

CashBox.name = fields.Text(
    string="Name",
    required=True,
)
CashBox.concept_id = fields.Many2one(
    'pos.box.concept',
    string='Concept',
    required=True,
    ondelete='cascade',
)
CashBox.onchange_concept_id = onchange_concept_id
#CashBox._run = _run


class CashBoxIn(models.TransientModel):
    _inherit = 'cash.box.in'

    @api.multi
    def _calculate_values_for_statement_line(self, record):
        # TODO: remove super() transfer_account_id check (see: addons/account/wizard/pos_box.py:49)
        vals = super(CashBoxIn, self)._calculate_values_for_statement_line(record)
        former_account_id = vals.get("account_id", False)
        vals["concept_id"] = self.concept_id.id
        vals["account_id"] = self.concept_id.account_id.id or former_account_id
        vals["line_type"] = "in"
        vals["state"] = "confirm"
        return vals


class CashBoxOut(models.TransientModel):
    _inherit = 'cash.box.out'

    @api.multi
    def _calculate_values_for_statement_line(self, record):
        # TODO: remove super() transfer_account_id check (see: addons/account/wizard/pos_box.py:67)
        vals = super(CashBoxOut, self)._calculate_values_for_statement_line(record)
        former_account_id = vals.get("account_id", False)
        vals["concept_id"] = self.concept_id.id
        vals["account_id"] = self.concept_id.account_id.id or former_account_id
        vals["line_type"] = "out"
        vals["state"] = "confirm"
        return vals
