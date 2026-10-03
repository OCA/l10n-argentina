# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class L10nArBankBank(models.Model):
    """Argentinian banks (BCRA entity list).

    Odoo 20 removed ``res.bank``: bank accounts point here by
    ``l10n_ar_bank_id``.
    """

    _name = "l10n_ar_bank.bank"
    _description = "Argentinian Bank"
    _order = "code, name"
    _rec_names_search = ("name", "code", "bic")

    name = fields.Char(required=True)
    code = fields.Char(
        string="BCRA Code",
        help="Entity code assigned by the Banco Central de la Republica Argentina. "
        "Its last three digits are the bank code of the CBU.",
    )
    bic = fields.Char(string="BIC/SWIFT")
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char()
    city = fields.Char()
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        domain="[('country_id', '=?', country_id)]",
    )
    country_id = fields.Many2one(comodel_name="res.country")
    phone = fields.Char()
    email = fields.Char()
    active = fields.Boolean(default=True)

    @api.depends("code", "name")
    def _compute_display_name(self):
        for bank in self:
            bank.display_name = f"{bank.code} - {bank.name}" if bank.code else bank.name
