# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_ar_withholding_certificate_number = fields.Char(
        string="Certificate number",
        copy=False,
        readonly=True,
        help="Numbered sequentially on the first printing of the withholding "
        "certificate (see ir.sequence l10n_ar_withholding_certificate). It only "
        "applies to applied withholding lines (tax_line_id with "
        "l10n_ar_withholding_payment_type = 'supplier').",
    )

    def _l10n_ar_withholding_ensure_certificate_number(self):
        """Assign a certificate number to the lines that do not have one yet.

        Idempotent: calling it again does not issue a new number for a line
        that already has one.

        Uses `next_by_code` (not `next_by_id` over a manual `search()`): it
        applies the company filter of `ir.sequence` itself (the global sequence
        registered by this module acts as a fallback; a company needing its own
        numbering can register a sequence with the same `code` and a
        `company_id` set, with no code change) and returns `False` gracefully
        instead of raising `AttributeError` if the sequence has been removed.
        """
        lines_without_number = self.filtered(
            lambda line: not line.l10n_ar_withholding_certificate_number
        )
        for line in lines_without_number:
            line.l10n_ar_withholding_certificate_number = self.env[
                "ir.sequence"
            ].next_by_code("l10n_ar_withholding_certificate")
