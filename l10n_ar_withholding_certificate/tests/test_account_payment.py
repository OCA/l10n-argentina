# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_ar.tests.common import TestArCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestAccountPaymentWithholdingCertificate(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.withholding_tax_base_account_id = cls.env.ref(
            f"account.{cls.env.company.id}_base_tax_account"
        )
        cls.withholding_account = cls.env["account.account"].create(
            {
                "name": "Withholdings to pay",
                "code": "WTH.CERT",
                "account_type": "liability_current",
            }
        )
        cls.certificate_sequence = cls.env["ir.sequence"].create(
            {
                "name": "Withholding certificates (test)",
                "implementation": "no_gap",
                "prefix": "CERT-",
                "padding": 6,
                "company_id": cls.env.company.id,
            }
        )
        # Applied when paying a vendor: this company is the withholding agent.
        cls.tax_applied = cls._create_withholding_tax(
            "IIBB WTH CABA 10% (test)",
            "purchase",
            l10n_ar_withholding_tax_type="iibb_untaxed",
            l10n_ar_state_id=cls.env.ref("base.state_ar_c").id,
            withholding_sequence_id=cls.certificate_sequence.id,
        )
        # Suffered when a customer pays us: the customer certifies it.
        cls.tax_suffered = cls._create_withholding_tax(
            "IIBB WTH suffered 1% (test)",
            "sale",
            l10n_ar_withholding_tax_type="iibb_untaxed",
        )

    @classmethod
    def _create_withholding_tax(cls, name, type_tax_use, **values):
        return cls.env["account.tax"].create(
            {
                "name": name,
                "amount_type": "percent",
                "amount": -10 if type_tax_use == "purchase" else -1,
                "type_tax_use": type_tax_use,
                "is_withholding_tax": True,
                "company_id": cls.env.company.id,
                "invoice_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "account_id": cls.withholding_account.id,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "account_id": cls.withholding_account.id,
                        }
                    ),
                ],
                **values,
            }
        )

    def _pay_with_withholding(self, move_type, tax, number=None):
        """Post a 1000 + 21% document of ADHOC and pay it through the core
        register payment wizard, withholding `tax` on the untaxed amount."""
        document_values = {}
        if move_type == "in_invoice":
            document_values["l10n_latam_document_number"] = "1-1"
        document = self._create_invoice_one_line(
            move_type=move_type,
            partner_id=self.res_partner_adhoc,
            invoice_date="2026-06-01",
            product_id=self.product_a,
            price_unit=1000.0,
            tax_ids=self.tax_21_purchase if move_type == "in_invoice" else self.tax_21,
            post=True,
            **document_values,
        )
        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=document.ids)
            .create({"payment_date": "2026-06-10"})
        )
        wizard.withholding_line_ids = [
            Command.clear(),
            Command.create(
                {
                    "tax_id": tax.id,
                    "base_amount": 1000.0,
                    "amount": 0,
                    "name": number,
                }
            ),
        ]
        wizard.withholding_line_ids._compute_amount()
        action = wizard.action_create_payments()
        return self.env["account.payment"].browse(action["res_id"])

    def _render_html(self, payment):
        html, _content_type = self.env["ir.actions.report"]._render_qweb_html(
            "l10n_ar_withholding_certificate.report_withholding_certificate",
            payment.ids,
        )
        return html.decode()

    def test_vendor_payment_certifies_the_applied_withholding(self):
        payment = self._pay_with_withholding("in_invoice", self.tax_applied)
        self.assertIn(payment.state, ("paid", "reconciled"))
        line = payment.l10n_ar_withholding_certificate_line_ids
        self.assertEqual(len(line), 1)
        self.assertEqual(line.tax_id, self.tax_applied)
        self.assertEqual(line.name, "CERT-000001")
        self.assertEqual(line.amount, 100.0)

        action = payment.with_context(
            discard_logo_check=True
        ).action_l10n_ar_print_withholding_certificate()
        self.assertEqual(
            action["report_name"],
            "l10n_ar_withholding_certificate.report_withholding_certificate",
        )
        html = self._render_html(payment)
        self.assertIn("CERT-000001", html)
        self.assertIn("30-71429569-8", html)  # withheld party CUIT
        self.assertIn("30-11111111-8", html)  # agent CUIT
        self.assertIn("Ciudad Autónoma de Buenos Aires", html)
        self.assertIn("1,000.00", html)
        self.assertIn("100.00", html)

    def test_printing_again_keeps_the_number_and_the_sequence(self):
        payment = self._pay_with_withholding("in_invoice", self.tax_applied)
        number = payment.l10n_ar_withholding_certificate_line_ids.name
        self.certificate_sequence.invalidate_recordset()
        next_number = self.certificate_sequence.number_next_actual

        payment.action_l10n_ar_print_withholding_certificate()
        self._render_html(payment)
        payment.action_l10n_ar_print_withholding_certificate()

        self.assertEqual(payment.l10n_ar_withholding_certificate_line_ids.name, number)
        self.certificate_sequence.invalidate_recordset()
        self.assertEqual(self.certificate_sequence.number_next_actual, next_number)

    def test_customer_collection_withholding_is_not_certified(self):
        payment = self._pay_with_withholding(
            "out_invoice", self.tax_suffered, number="0001-00000042"
        )
        self.assertIn(payment.state, ("paid", "reconciled"))
        # The core keeps the suffered withholding on the payment...
        self.assertEqual(payment.withholding_line_ids.tax_id, self.tax_suffered)
        # ...but it is not ours to certify.
        self.assertFalse(payment.l10n_ar_withholding_certificate_line_ids)
        with self.assertRaises(UserError):
            payment.action_l10n_ar_print_withholding_certificate()
        self.assertNotIn("0001-00000042", self._render_html(payment))

    def test_draft_payment_is_not_certified(self):
        payment = self._pay_with_withholding("in_invoice", self.tax_applied)
        payment.action_draft()
        self.assertEqual(payment.state, "draft")
        self.assertFalse(payment.l10n_ar_withholding_certificate_line_ids)
        with self.assertRaises(UserError):
            payment.action_l10n_ar_print_withholding_certificate()
