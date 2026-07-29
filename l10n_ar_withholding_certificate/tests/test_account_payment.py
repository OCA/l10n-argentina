# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.l10n_ar.tests.common import TestArCommon


@tagged("post_install", "-at_install")
class TestAccountPaymentWithholdingCertificate(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.withholding_tax = cls.env["account.tax"].create(
            {
                "name": "Retención Ganancias (prueba)",
                "amount": 0,
                "type_tax_use": "none",
                "l10n_ar_withholding_payment_type": "supplier",
                "company_id": cls.company_ri.id,
            }
        )
        bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.company_ri.id)], limit=1
        )
        cls.payment = cls.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": cls.res_partner_adhoc.id,
                "amount": 1000.0,
                "journal_id": bank_journal.id,
            }
        )
        cls.payment.action_post()
        # Withholding line plus counterpart line in the same create(), so the
        # addition stays balanced (Odoo 18 validates the balance even when
        # attaching a line to an already posted move). The goal here is to test
        # the numbering and the report of this module, not the full withholding
        # registration flow of l10n_ar_withholding, which is core territory.
        # tax_line_id is related='tax_repartition_line_id.tax_id' (Odoo 18):
        # setting tax_line_id directly is ignored, the repartition line is
        # required.
        repartition_line = cls.withholding_tax.invoice_repartition_line_ids.filtered(
            lambda r: r.repartition_type == "tax"
        )[:1]
        account_id = cls.payment.move_id.line_ids[0].account_id.id
        cls.env["account.move.line"].create(
            [
                {
                    "move_id": cls.payment.move_id.id,
                    "name": "Retención Ganancias",
                    "account_id": account_id,
                    "tax_repartition_line_id": repartition_line.id,
                    "tax_base_amount": 1000.0,
                    "debit": 0.0,
                    "credit": 30.0,
                },
                {
                    "move_id": cls.payment.move_id.id,
                    "name": "Contrapartida (prueba)",
                    "account_id": account_id,
                    "debit": 30.0,
                    "credit": 0.0,
                },
            ]
        )
        # Invalidate the cache of the MOVE (not only of the payment): it is
        # move.line_ids that the l10n_ar_withholding_ids compute depends on, and
        # that is what went stale.
        cls.payment.move_id.invalidate_recordset()
        cls.payment.invalidate_recordset()

    def test_only_withholding_lines_get_a_certificate_number(self):
        lines = self.payment.l10n_ar_withholding_ids
        self.assertEqual(len(lines), 1)
        self.assertFalse(lines.l10n_ar_withholding_certificate_number)

        lines._l10n_ar_withholding_ensure_certificate_number()
        self.assertTrue(lines.l10n_ar_withholding_certificate_number)

        # Regression: numbering may only touch the withholding line, never the
        # counterpart line (nor any other line of the move).
        other_lines = self.payment.move_id.line_ids - lines
        self.assertTrue(other_lines)
        self.assertFalse(
            any(other_lines.mapped("l10n_ar_withholding_certificate_number"))
        )

    def test_number_is_idempotent_and_consumes_the_sequence_once(self):
        sequence = self.env["ir.sequence"].search(
            [("code", "=", "l10n_ar_withholding_certificate")], limit=1
        )
        # `next_by_code` increments through direct SQL, bypassing the ORM
        # cache: it has to be invalidated before reading `number_next_actual`
        # again, otherwise the Python read stays stuck on the cached value.
        sequence.invalidate_recordset()
        number_before = sequence.number_next_actual

        lines = self.payment.l10n_ar_withholding_ids
        lines._l10n_ar_withholding_ensure_certificate_number()
        first_number = lines.l10n_ar_withholding_certificate_number
        sequence.invalidate_recordset()
        self.assertEqual(sequence.number_next_actual, number_before + 1)

        lines._l10n_ar_withholding_ensure_certificate_number()
        self.assertEqual(lines.l10n_ar_withholding_certificate_number, first_number)
        # The second call is idempotent: it does not consume the sequence again.
        sequence.invalidate_recordset()
        self.assertEqual(sequence.number_next_actual, number_before + 1)

    def test_print_button_renders_the_pdf_with_the_withheld_amount(self):
        action = self.payment.action_l10n_ar_print_withholding_certificate()
        self.assertTrue(action)
        certificate_number = (
            self.payment.l10n_ar_withholding_ids.l10n_ar_withholding_certificate_number
        )
        self.assertTrue(certificate_number)

        pdf_content, _content_type = self.env["ir.actions.report"]._render_qweb_pdf(
            "l10n_ar_withholding_certificate.report_withholding_certificate",
            res_ids=self.payment.ids,
        )
        self.assertTrue(pdf_content)

        # The PDF is binary (compressed streams): check the real content
        # through the HTML rendered before the conversion, not the PDF bytes.
        html_content, _content_type = self.env["ir.actions.report"]._render_qweb_html(
            "l10n_ar_withholding_certificate.report_withholding_certificate",
            self.payment.ids,
        )
        html_text = html_content.decode("utf-8")
        self.assertIn(certificate_number, html_text)
        self.assertIn("30", html_text)  # withheld amount, without a negative sign

    def _create_customer_payment_with_suffered_withholding(self):
        """Customer collection carrying a withholding SUFFERED by the company."""
        customer_withholding_tax = self.env["account.tax"].create(
            {
                "name": "Retención sufrida IIBB (prueba)",
                "amount": 0,
                "type_tax_use": "none",
                "l10n_ar_withholding_payment_type": "customer",
                "company_id": self.company_ri.id,
            }
        )
        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", self.company_ri.id)], limit=1
        )
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.res_partner_adhoc.id,
                "amount": 1000.0,
                "journal_id": bank_journal.id,
            }
        )
        payment.action_post()
        repartition_line = (
            customer_withholding_tax.invoice_repartition_line_ids.filtered(
                lambda r: r.repartition_type == "tax"
            )[:1]
        )
        account_id = payment.move_id.line_ids[0].account_id.id
        self.env["account.move.line"].create(
            [
                {
                    "move_id": payment.move_id.id,
                    "name": "Retención sufrida",
                    "account_id": account_id,
                    "tax_repartition_line_id": repartition_line.id,
                    "tax_base_amount": 1000.0,
                    "debit": 20.0,
                    "credit": 0.0,
                },
                {
                    "move_id": payment.move_id.id,
                    "name": "Contrapartida (prueba)",
                    "account_id": account_id,
                    "debit": 0.0,
                    "credit": 20.0,
                },
            ]
        )
        payment.move_id.invalidate_recordset()
        payment.invalidate_recordset()
        return payment

    def test_customer_suffered_withholding_stays_out_of_the_certificate(self):
        """The Certificado de Retencion is issued by the withholding agent.

        Regression: the button used the core `l10n_ar_withholding_ids`, which
        mixes both directions. On a customer collection with a suffered
        withholding, the company issued a certificate over a tax it had
        suffered, and consumed a number from the legal sequence on top of that.
        """
        payment = self._create_customer_payment_with_suffered_withholding()

        # The core sees the line (and the button used exactly this field).
        self.assertTrue(payment.l10n_ar_withholding_ids)
        # But it is not a withholding practised by us.
        self.assertFalse(payment.l10n_ar_supplier_withholding_ids)

    def test_customer_payment_raises_without_consuming_the_sequence(self):
        from odoo.exceptions import UserError

        payment = self._create_customer_payment_with_suffered_withholding()
        with self.assertRaises(UserError):
            payment.action_l10n_ar_print_withholding_certificate()

        # The legal sequence must not have been consumed.
        self.assertFalse(
            any(
                payment.l10n_ar_withholding_ids.mapped(
                    "l10n_ar_withholding_certificate_number"
                )
            ),
            "official number stored on a withholding that is not ours to certify",
        )

    def test_practised_withholding_still_enters_the_certificate(self):
        """The path that already worked has to keep working."""
        self.assertTrue(self.payment.l10n_ar_supplier_withholding_ids)
        self.assertEqual(
            self.payment.l10n_ar_supplier_withholding_ids,
            self.payment.l10n_ar_withholding_ids,
        )
