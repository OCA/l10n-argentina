# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.l10n_ar.tests.common import TestArCommon


@tagged("post_install", "-at_install")
class TestAccountVatLedger(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # Pre-printed point of sale (II_IM), not "Online Invoice" (RLI_RLM):
        # the VAT ledger does not depend on electronic invoicing, and an
        # electronic journal would make the `_post()` of l10n_ar_arca_edi (when
        # installed on the same database) actually request a CAE during these
        # tests.
        cls.sale_journal = cls._create_journal(
            "wsfe",
            data={
                "l10n_ar_afip_pos_system": "II_IM",
                "l10n_ar_afip_pos_number": "3",
            },
        )
        cls.sale_invoice = cls._create_invoice_ar(
            journal_id=cls.sale_journal.id,
            partner_id=cls.res_partner_adhoc.id,
            invoice_date="2026-06-15",
            invoice_line_ids=[
                cls._prepare_invoice_line(
                    price_unit=1000.0, product_id=cls.product_iva_21
                )
            ],
        )
        cls.sale_invoice.action_post()
        cls.sale_invoice.l10n_latam_document_type_id.export_to_digital = True

        cls.purchase_journal = cls._create_journal(
            "wsfe", data={"type": "purchase", "l10n_ar_afip_pos_number": "1"}
        )
        cls.vendor_bill = cls._create_invoice_ar(
            move_type="in_invoice",
            journal_id=cls.purchase_journal.id,
            partner_id=cls.res_partner_adhoc.id,
            invoice_date="2026-06-20",
            invoice_line_ids=[
                cls._prepare_invoice_line(
                    price_unit=500.0, product_id=cls.product_iva_21
                )
            ],
        )
        cls.vendor_bill.l10n_latam_document_number = "00001-00000456"
        cls.vendor_bill.action_post()
        cls.vendor_bill.l10n_latam_document_type_id.export_to_digital = True

    def _create_ledger(self, ledger_type, journal):
        return self.env["account.vat.ledger"].create(
            {
                "type": ledger_type,
                "journal_ids": [(6, 0, journal.ids)],
                "date_from": "2026-06-01",
                "date_to": "2026-06-30",
            }
        )

    def test_compute_data_finds_the_customer_invoice_in_the_period(self):
        ledger = self._create_ledger("sale", self.sale_journal)
        self.assertIn(self.sale_invoice, ledger.invoice_ids)

    def test_sales_vat_ledger_builds_the_txt_without_raising(self):
        # Regression: document_number/l10n_ar_currency_rate (fields from the
        # ADHOC 14.0 era, absent from the 18.0 core) made this method raise
        # every time. It is the only code path exercising _l10n_ar_get_amounts,
        # _l10n_ar_get_document_number_parts and the currency computation of
        # this module.
        ledger = self._create_ledger("sale", self.sale_journal)
        ledger.compute_digital_data()
        self.assertTrue(ledger.REGDIGITAL_CV_CBTE)
        row = ledger.REGDIGITAL_CV_CBTE
        # Layout: Campo1 Fecha (8), Campo2 Tipo Comprobante (3), Campo3 Punto
        # de Venta (5). Checks that the point of sale number of the invoice (3)
        # was used, not a value wrongly extracted from the entry name.
        self.assertEqual(row[11:16], "00003")

    def test_purchase_vat_ledger_requires_the_vendor_document(self):
        partner_without_vat = self.env["res.partner"].create(
            {
                "name": "Sin CUIT",
                "country_id": self.env.ref("base.ar").id,
                "l10n_latam_identification_type_id": self.env.ref("l10n_ar.it_cuit").id,
                "l10n_ar_afip_responsibility_type_id": self.env.ref(
                    "l10n_ar.res_IVARI"
                ).id,
            }
        )
        bill_without_vat = self._create_invoice_ar(
            move_type="in_invoice",
            journal_id=self.purchase_journal.id,
            partner_id=partner_without_vat.id,
            invoice_date="2026-06-22",
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=200.0, product_id=self.product_iva_21
                )
            ],
        )
        bill_without_vat.l10n_latam_document_number = "00001-00000999"
        bill_without_vat.action_post()

        ledger = self._create_ledger("purchase", self.purchase_journal)
        with self.assertRaises(ValidationError):
            ledger.compute_digital_data()

    def test_purchase_vat_ledger_builds_the_txt_without_raising(self):
        ledger = self._create_ledger("purchase", self.purchase_journal)
        ledger.compute_digital_data()
        self.assertTrue(ledger.REGDIGITAL_CV_CBTE)

    def test_state_transitions(self):
        ledger = self._create_ledger("sale", self.sale_journal)
        self.assertEqual(ledger.state, "draft")
        ledger.action_present()
        self.assertEqual(ledger.state, "presented")
        ledger.action_cancel()
        self.assertEqual(ledger.state, "cancel")
        ledger.action_to_draft()
        self.assertEqual(ledger.state, "draft")

    def test_unimplemented_prorate_tax_credit_raises_a_clear_error(self):
        ledger = self._create_ledger("purchase", self.purchase_journal)
        ledger.prorate_tax_credit = True
        with self.assertRaises(ValidationError):
            ledger.compute_digital_data()

    def test_partner_document_is_sanitized_for_every_responsibility(self):
        """Regression inherited from the 14.0 [FIX]: the file uses fixed
        positions, so a separator in the CUIT shifts every following field of
        the line. Before the fix only Consumidor Final was sanitized.
        """
        ledger = self._create_ledger("purchase", self.purchase_journal)
        partner = self.env["res.partner"].create(
            {
                "name": "Contacto con CUIT formateado",
                "vat": "30-71429569-8",
                "l10n_latam_identification_type_id": self.env.ref("l10n_ar.it_cuit").id,
                "l10n_ar_afip_responsibility_type_id": self.env.ref(
                    "l10n_ar.res_IVARI"
                ).id,
            }
        )
        number = ledger.get_partner_document_number(partner)
        self.assertEqual(number, "00000000030714295698")
        self.assertEqual(len(number), 20)

    def test_partner_without_vat_raises(self):
        ledger = self._create_ledger("purchase", self.purchase_journal)
        partner = self.env["res.partner"].create({"name": "Sin identificación"})
        with self.assertRaises(ValidationError):
            ledger.get_partner_document_number(partner)

    def test_aliquots_count_matches_the_generated_records(self):
        """Regression inherited from the 14.0 [FIX]: Campo 19 has to match the
        number of REGDIGITAL_CV_ALICUOTAS records, which come from the core
        `_get_vat()`. A tax without a VAT code (an IIBB perception) used to be
        counted here while producing no record there.
        """
        self.tax_perc_iibb.amount = 3.0
        invoice = self._create_invoice_ar(
            journal_id=self.sale_journal.id,
            partner_id=self.res_partner_adhoc.id,
            invoice_date="2026-06-16",
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=1000.0,
                    product_id=self.product_iva_21,
                    tax_ids=[Command.set([self.tax_21.id, self.tax_perc_iibb.id])],
                )
            ],
        )
        invoice.action_post()
        ledger = self._create_ledger("sale", self.sale_journal)
        self.assertEqual(
            ledger._get_aliquots(invoice),
            len(invoice._get_vat()),
            "Campo 19 must match the number of rate records",
        )
