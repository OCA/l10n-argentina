import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    tax_type = fields.Selection(
        selection=[
            ("vat", "IVA"),
            ("withholdings", "Percepciones/Retenciones"),
            ("exempt", "Exentos"),
        ],
        string="Tipo de Impuestos",
    )
