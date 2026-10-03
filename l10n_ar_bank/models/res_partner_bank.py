# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

# Bank account fields filled from the selected Argentinian bank.
BANK_FIELDS = {
    "bank_name": "name",
    "bank_bic": "bic",
    "street": "street",
    "street2": "street2",
    "zip": "zip",
    "city": "city",
    "state_id": "state_id",
}


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    l10n_ar_bank_id = fields.Many2one(
        comodel_name="l10n_ar_bank.bank",
        string="Argentinian Bank",
        help="Bank from the BCRA entity list. Fills the bank name, BIC and "
        "address of the account.",
    )
    bank_name = fields.Char(
        compute="_compute_l10n_ar_bank_data", store=True, readonly=False
    )
    bank_bic = fields.Char(
        compute="_compute_l10n_ar_bank_data", store=True, readonly=False
    )
    street = fields.Char(
        compute="_compute_l10n_ar_bank_data", store=True, readonly=False
    )
    street2 = fields.Char(
        compute="_compute_l10n_ar_bank_data", store=True, readonly=False
    )
    zip = fields.Char(compute="_compute_l10n_ar_bank_data", store=True, readonly=False)
    city = fields.Char(compute="_compute_l10n_ar_bank_data", store=True, readonly=False)
    state_id = fields.Many2one(
        compute="_compute_l10n_ar_bank_data", store=True, readonly=False
    )

    @api.depends("l10n_ar_bank_id")
    def _compute_l10n_ar_bank_data(self):
        for account in self:
            bank = account.l10n_ar_bank_id
            for account_field, bank_field in BANK_FIELDS.items():
                # Without a bank, keep what was typed on the account.
                account[account_field] = (
                    bank[bank_field] if bank else account[account_field]
                )
