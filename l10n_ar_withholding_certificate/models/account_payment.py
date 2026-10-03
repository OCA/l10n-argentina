# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_ar_withholding_certificate_line_ids = fields.Many2many(
        comodel_name="account.payment.withholding.line",
        string="Certified withholdings",
        compute="_compute_l10n_ar_withholding_certificate_line_ids",
        help="Withholdings this company applied as withholding agent on this "
        "posted vendor payment. This is what the Certificado de Retención "
        "evidences.",
    )

    @api.depends(
        "state",
        "payment_type",
        "withholding_line_ids.tax_id.type_tax_use",
        "withholding_line_ids.name",
    )
    def _compute_l10n_ar_withholding_certificate_line_ids(self):
        """Keep the withholdings practised as agent, apart from the suffered ones.

        A withholding suffered on a customer collection (sale tax) is evidenced
        by the certificate the customer issues, and the number is only given
        once the payment is posted.
        """
        for payment in self:
            if (
                payment.state not in ("paid", "reconciled")
                or payment.payment_type != "outbound"
            ):
                payment.l10n_ar_withholding_certificate_line_ids = False
                continue
            payment.l10n_ar_withholding_certificate_line_ids = (
                payment.withholding_line_ids.filtered(
                    lambda line: line.tax_id.type_tax_use == "purchase" and line.name
                )
            )

    def action_l10n_ar_print_withholding_certificate(self):
        if not self.l10n_ar_withholding_certificate_line_ids:
            raise UserError(
                self.env._(
                    "There are no withholdings applied by this company on a "
                    "posted vendor payment. The Certificado de Retención is "
                    "issued by the withholding agent; a withholding suffered "
                    "on a customer collection is evidenced by the certificate "
                    "the customer issues."
                )
            )
        return self.env.ref(
            "l10n_ar_withholding_certificate.action_report_withholding_certificate"
        ).report_action(self)
