##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.account.wizard.pos_box import CashBox as CashBoxOdoo
from odoo.addons.account.wizard.pos_box import CashBoxIn as CashBoxInOdoo
from odoo.addons.account.wizard.pos_box import CashBoxOut as CashBoxOutOdoo


@api.multi
def _run_patched(self, records):
    for box in self:
        for record in records:
            if not record.journal_id:
                raise UserError(
                    _("Please check that the field 'Journal' " +
                      "is set on the Bank Statement"))
            box._create_bank_statement_line(record)
    return {}


@api.multi
def get_account(self, record=None):
    """ Provides hook to set an account on cash.box movements """
    res = self.concept_id.account_id
    fallback = record.journal_id.company_id.transfer_account_id
    if not res and not fallback:
        raise ValidationError(
            _('Cannot found account to do the transfer'))
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
        CashBoxOdoo._patch_method(
            '_run',
            _run_patched
        )
        return res

    @api.multi
    def _calculate_values_for_statement_line(self, record):
        vals = super(CashBoxIn, self)._calculate_values_for_statement_line(
            record)
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
        return res

    @api.multi
    def _calculate_values_for_statement_line(self, record):
        vals = super(CashBoxOut, self)._calculate_values_for_statement_line(
            record)
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
