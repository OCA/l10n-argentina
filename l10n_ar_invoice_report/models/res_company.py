# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    show_invoice_payment_methods_info = fields.Boolean(
        "Show payment methods in invoice", default=True
    )
    show_invoice_account_debt_info = fields.Boolean(
        "Show partner current account debt in invoice", default=True
    )
    show_logo_on_footer = fields.Boolean("Show logo on footer", default=True)
    invoice_background_image = fields.Binary("Invoice background image")
    invoice_mercadopago_qr = fields.Binary("QR Mercadopago")
    invoice_payment_terms = fields.Text(
        "Invoice payment terms",
    )
    invoice_fixed_terms = fields.Text(
        "Invoice Fixed Terms",
    )
