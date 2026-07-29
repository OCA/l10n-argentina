# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_ar_supplier_withholding_ids = fields.Many2many(
        comodel_name="account.move.line",
        string="Withholdings applied",
        compute="_compute_l10n_ar_supplier_withholding_ids",
        help="Withholdings this company applied as withholding agent when "
        "paying. This is what the Certificado de Retención evidences.",
    )

    # Depends on `move_id.line_ids`, not on `l10n_ar_withholding_ids`: the core
    # field is a non-stored, non-searchable compute, and Odoo 18 requires every
    # field in a `depends` chain to be searchable (otherwise it emits a
    # UserWarning, which fails the OCA checklog). It is the same dependency the
    # core itself declares on `_compute_l10n_ar_withholding_ids`.
    @api.depends("move_id.line_ids")
    def _compute_l10n_ar_supplier_withholding_ids(self):
        """Tell the withholding practised apart from the one suffered.

        The core `l10n_ar_withholding_ids` mixes both directions: the
        withholding the company applies when paying a vendor (`supplier`) and
        the one it suffers when collecting from a customer (`customer`). Only
        the first produces a Certificado de Retención issued by us; the second
        is evidenced by the certificate the customer issues. Without that
        split, the button showed up on a customer collection and the legal
        sequence was consumed to number a withholding that is not ours to
        certify.
        """
        for payment in self:
            payment.l10n_ar_supplier_withholding_ids = (
                payment.l10n_ar_withholding_ids.filtered(
                    lambda line: (
                        line.tax_line_id.l10n_ar_withholding_payment_type == "supplier"
                    )
                )
            )

    def action_l10n_ar_print_withholding_certificate(self):
        # `l10n_ar_withholding_ids` already exists in the core
        # (l10n_ar_withholding) with the same related field: reuse it instead of
        # duplicating it.
        lines = self.l10n_ar_supplier_withholding_ids
        if not lines:
            raise UserError(
                _(
                    "There are no withholdings applied by this company on this "
                    "payment. The Certificado de Retención is issued by the "
                    "withholding agent, that is, only for the withholding the "
                    "company applied when paying a vendor. A withholding the "
                    "company suffered when collecting from a customer is "
                    "evidenced by the certificate the customer issues."
                )
            )
        lines._l10n_ar_withholding_ensure_certificate_number()
        return self.env.ref(
            "l10n_ar_withholding_certificate.action_report_withholding_certificate"
        ).report_action(self)
