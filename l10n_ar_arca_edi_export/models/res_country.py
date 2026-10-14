# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCountry(models.Model):
    _inherit = "res.country"

    l10n_ar_arca_cuit_pais = fields.Char(
        string="CUIT País (ARCA)",
        help="Code ARCA assigns to each country to identify the foreign "
        "taxpayer in WSFEXv1 (Cuit_pais_cliente). It is a table of ARCA's own, "
        "distinct from the country code (l10n_ar_afip_code) the core already "
        "ships.\n\n"
        "It comes empty: the full table was not obtained from an official ARCA "
        "source, and filling in some 200 countries by deduction would be worse "
        "than leaving it blank (the module raises a clear error when it is "
        "missing, instead of sending a wrong number). Fill in the destination "
        "country by hand before invoicing an export to it, checking the "
        "official ARCA CUIT País table.",
    )
