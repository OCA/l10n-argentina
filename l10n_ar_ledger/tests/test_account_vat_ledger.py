# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import io

import openpyxl

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.l10n_ar.tests.common import TestArCommon

# Fixed width layout of REGDIGITAL_CV_CBTE (sales), up to field 19.
SALE_CBTE_LAYOUT = [
    ("date", 8),
    ("document_type", 3),
    ("point_of_sale", 5),
    ("number", 20),
    ("number_to", 20),
    ("partner_document_code", 2),
    ("partner_document_number", 20),
    ("partner_name", 30),
    ("amount_total", 15),
    ("untaxed_base", 15),
    ("non_categorized_perception", 15),
    ("exempt_base", 15),
    ("national_perception", 15),
    ("iibb_perception", 15),
    ("municipal_perception", 15),
    ("internal_taxes", 15),
    ("currency", 3),
    ("currency_rate", 10),
    ("aliquots_count", 1),
]

# Fixed width layout of REGDIGITAL_CV_CBTE (purchases), up to field 22 (ARCA
# design LIBRO_IVA_DIGITAL_COMPRAS_CBTE, positions 1 to 269).
PURCHASE_CBTE_LAYOUT = [
    ("date", 8),
    ("document_type", 3),
    ("point_of_sale", 5),
    ("number", 20),
    ("import_dispatch", 16),
    ("partner_document_code", 2),
    ("partner_document_number", 20),
    ("partner_name", 30),
    ("amount_total", 15),
    ("untaxed_base", 15),
    ("exempt_base", 15),
    ("vat_perception", 15),
    ("national_perception", 15),
    ("iibb_perception", 15),
    ("municipal_perception", 15),
    ("internal_taxes", 15),
    ("currency", 3),
    ("currency_rate", 10),
    ("aliquots_count", 1),
    ("operation_code", 1),
    ("computable_vat_credit", 15),
    ("other_taxes", 15),
]


def split_fixed(row, layout):
    values = {}
    position = 0
    for name, size in layout:
        values[name] = row[position : position + size]
        position += size
    return values


@tagged("post_install", "-at_install")
class TestAccountVatLedger(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.tax_perc_iibb.amount = 3.0
        cls.doc_invoice_a = cls.env.ref("l10n_ar.dc_a_f")
        cls.doc_credit_note_a = cls.env.ref("l10n_ar.dc_a_nc")
        (cls.doc_invoice_a | cls.doc_credit_note_a).export_to_digital = True

        # Pre-printed point of sale (II_IM), not "Online Invoice": the VAT
        # ledger does not depend on electronic invoicing, and an electronic
        # journal would make an EDI module installed on the same database
        # request a CAE during these tests.
        cls.sale_journal = cls._create_journal(
            "wsfe",
            data={
                "l10n_ar_afip_pos_system": "II_IM",
                "l10n_ar_afip_pos_number": "3",
            },
        )
        cls.other_sale_journal = cls._create_journal(
            "wsfe",
            data={
                "l10n_ar_afip_pos_system": "II_IM",
                "l10n_ar_afip_pos_number": "4",
            },
        )
        # 1000 at 21% with a 3% IIBB perception, plus 500 at 10.5%:
        # 1500 untaxed + 210 + 52.50 VAT + 30 IIBB = 1792.50
        cls.sale_invoice = cls._create_invoice_ar(
            journal_id=cls.sale_journal.id,
            partner_id=cls.res_partner_adhoc.id,
            invoice_date="2026-06-15",
            invoice_line_ids=[
                cls._prepare_invoice_line(
                    price_unit=1000.0,
                    product_id=cls.product_iva_21,
                    tax_ids=[Command.set([cls.tax_21.id, cls.tax_perc_iibb.id])],
                ),
                cls._prepare_invoice_line(
                    price_unit=500.0,
                    product_id=cls.product_iva_105,
                    tax_ids=[Command.set(cls.tax_10_5.ids)],
                ),
            ],
        )
        cls.sale_invoice.action_post()

        # Moves the ledger must leave out: a draft, one out of the period and
        # one in a journal the ledger does not cover.
        cls.draft_invoice = cls._create_invoice_ar(
            journal_id=cls.sale_journal.id,
            partner_id=cls.res_partner_adhoc.id,
            invoice_date="2026-06-10",
        )
        # Posted and reset to draft: it keeps its name, only the state tells.
        cls.reset_invoice = cls._create_invoice_ar(
            journal_id=cls.sale_journal.id,
            partner_id=cls.res_partner_adhoc.id,
            invoice_date="2026-06-11",
        )
        cls.reset_invoice.action_post()
        cls.reset_invoice.button_draft()
        cls.next_period_invoice = cls._create_invoice_ar(
            journal_id=cls.sale_journal.id,
            partner_id=cls.res_partner_adhoc.id,
            invoice_date="2026-07-01",
        )
        cls.next_period_invoice.action_post()
        cls.other_journal_invoice = cls._create_invoice_ar(
            journal_id=cls.other_sale_journal.id,
            partner_id=cls.res_partner_adhoc.id,
            invoice_date="2026-06-12",
        )
        cls.other_journal_invoice.action_post()

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
                    price_unit=500.0,
                    product_id=cls.product_iva_21,
                    tax_ids=[Command.set(cls.tax_21_purchase.ids)],
                )
            ],
        )
        cls.vendor_bill.l10n_latam_document_number = "00001-00000456"
        cls.vendor_bill.action_post()

    def _create_ledger(self, ledger_type, journals):
        return self.env["account.vat.ledger"].create(
            {
                "type": ledger_type,
                "journal_ids": [Command.set(journals.ids)],
                "date_from": "2026-06-01",
                "date_to": "2026-06-30",
            }
        )

    def _cbte_rows(self, ledger):
        ledger.compute_digital_data()
        return ledger.REGDIGITAL_CV_CBTE.split("\r\n")

    def test_compute_data_takes_the_posted_moves_of_the_period_and_journals(self):
        ledger = self._create_ledger("sale", self.sale_journal)
        self.assertTrue(self.reset_invoice.name)
        self.assertEqual(ledger.invoice_ids, self.sale_invoice)

        ledger.journal_ids = [Command.link(self.other_sale_journal.id)]
        self.assertEqual(
            ledger.invoice_ids, self.other_journal_invoice | self.sale_invoice
        )
        self.assertEqual(
            ledger.invoice_ids.mapped("invoice_date"),
            sorted(ledger.invoice_ids.mapped("invoice_date")),
        )

    def test_sales_voucher_record(self):
        ledger = self._create_ledger("sale", self.sale_journal)
        rows = self._cbte_rows(ledger)
        self.assertEqual(len(rows), 1)
        row = split_fixed(rows[0], SALE_CBTE_LAYOUT)
        number = self.sale_invoice._l10n_ar_get_document_number_parts(
            self.sale_invoice.l10n_latam_document_number, "1"
        )["invoice_number"]
        self.assertEqual(row["date"], "20260615")
        self.assertEqual(row["document_type"], "001")
        self.assertEqual(row["point_of_sale"], "00003")
        self.assertEqual(row["number"], str(number).zfill(20))
        self.assertEqual(row["number_to"], str(number).zfill(20))
        self.assertEqual(row["partner_document_code"], "80")
        self.assertEqual(row["partner_document_number"], "00000000030714295698")
        self.assertEqual(row["partner_name"], "ADHOC SA".ljust(30))
        self.assertEqual(row["amount_total"], "000000000179250")
        self.assertEqual(row["iibb_perception"], "000000000003000")
        self.assertEqual(row["exempt_base"], "0" * 15)
        self.assertEqual(row["currency"], "PES")
        self.assertEqual(row["currency_rate"], "0001000000")
        self.assertEqual(row["aliquots_count"], "2")

    def test_sales_aliquot_records_by_rate(self):
        ledger = self._create_ledger("sale", self.sale_journal)
        ledger.compute_digital_data()
        records = ledger.REGDIGITAL_CV_ALICUOTAS.split("\r\n")
        prefix = records[0][:28]
        self.assertTrue(all(record[:28] == prefix for record in records))
        self.assertEqual(prefix[:8], "00100003")
        # Base (15), ARCA VAT code (4) and tax amount (15) per rate.
        self.assertEqual(
            sorted(record[28:] for record in records),
            sorted(
                [
                    "0000000001000000005000000000021000",
                    "0000000000500000004000000000005250",
                ]
            ),
        )

    def test_credit_note_amounts_are_reported_unsigned(self):
        refund = self._create_invoice_ar(
            move_type="out_refund",
            journal_id=self.sale_journal.id,
            partner_id=self.res_partner_adhoc.id,
            invoice_date="2026-06-25",
            l10n_latam_document_type_id=self.doc_credit_note_a.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=100.0,
                    product_id=self.product_iva_21,
                    tax_ids=[Command.set(self.tax_21.ids)],
                )
            ],
        )
        refund.action_post()
        ledger = self._create_ledger("sale", self.sale_journal)
        rows = [split_fixed(row, SALE_CBTE_LAYOUT) for row in self._cbte_rows(ledger)]
        refund_row = [row for row in rows if row["document_type"] == "003"]
        self.assertEqual(len(refund_row), 1)
        self.assertEqual(refund_row[0]["amount_total"], "000000000012100")
        self.assertIn(
            "0000000000100000005000000000002100", (ledger.REGDIGITAL_CV_ALICUOTAS)
        )

    def test_purchase_voucher_and_aliquot_records(self):
        ledger = self._create_ledger("purchase", self.purchase_journal)
        rows = self._cbte_rows(ledger)
        self.assertEqual(len(rows), 1)
        row = split_fixed(rows[0], PURCHASE_CBTE_LAYOUT)
        self.assertEqual(row["date"], "20260620")
        self.assertEqual(row["document_type"], "001")
        self.assertEqual(row["point_of_sale"], "00001")
        self.assertEqual(row["number"], "456".zfill(20))
        self.assertEqual(row["import_dispatch"], " " * 16)
        self.assertEqual(row["partner_document_code"], "80")
        self.assertEqual(row["partner_document_number"], "00000000030714295698")
        self.assertEqual(row["amount_total"], "000000000060500")
        # Vendor document code and number come before the amounts in the
        # purchase aliquot record.
        self.assertEqual(
            ledger.REGDIGITAL_CV_ALICUOTAS,
            "001"
            "00001" + "456".zfill(20) + "80" + "00000000030714295698"
            "000000000050000"
            "0005"
            "000000000010500",
        )
        self.assertFalse(ledger.REGDIGITAL_CV_COMPRAS_IMPORTACIONES)

    def test_purchase_computable_vat_credit_is_the_vat_only(self):
        """Field 21 (Credito Fiscal Computable) without proration is the VAT
        assessed of the voucher (ARCA specification, field 21): it must not
        add the taxable base nor the untaxed amounts."""
        bill = self._create_invoice_ar(
            move_type="in_invoice",
            journal_id=self.purchase_journal.id,
            partner_id=self.res_partner_adhoc.id,
            invoice_date="2026-06-21",
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=500.0,
                    product_id=self.product_iva_21,
                    tax_ids=[Command.set(self.tax_21_purchase.ids)],
                ),
                self._prepare_invoice_line(
                    price_unit=1000.0,
                    product_id=self.product_iva_105,
                    tax_ids=[Command.set(self._search_tax("iva_105", "purchase").ids)],
                ),
                self._prepare_invoice_line(
                    price_unit=200.0,
                    product_id=self.product_iva_21,
                    tax_ids=[Command.set(self.tax_no_gravado_purchase.ids)],
                ),
            ],
        )
        bill.l10n_latam_document_number = "00001-00000457"
        bill.action_post()
        ledger = self._create_ledger("purchase", self.purchase_journal)
        rows = self._cbte_rows(ledger)
        row = split_fixed(rows[1], PURCHASE_CBTE_LAYOUT)
        self.assertEqual(row["number"], "457".zfill(20))
        self.assertEqual(row["aliquots_count"], "2")
        # 21% on 500.00 plus 10.5% on 1000.00: 105.00 + 105.00 of VAT.
        self.assertEqual(row["computable_vat_credit"], "000000000021000")
        # The first bill of the period: 21% on 500.00.
        first = split_fixed(rows[0], PURCHASE_CBTE_LAYOUT)
        self.assertEqual(first["computable_vat_credit"], "000000000010500")
        self.assertEqual(len(rows[0]), 325)

    def test_digital_files_are_the_records_in_latin1(self):
        ledger = self._create_ledger("sale", self.sale_journal)
        ledger.compute_digital_data()
        self.assertEqual(
            ledger.digital_vouchers_file.content.decode("ISO-8859-1"),
            ledger.REGDIGITAL_CV_CBTE,
        )
        self.assertEqual(
            ledger.digital_aliquots_file.content.decode("ISO-8859-1"),
            ledger.REGDIGITAL_CV_ALICUOTAS,
        )
        self.assertEqual(
            ledger.digital_vouchers_filename, "Vouchers_sale_2026-06-30.txt"
        )
        self.assertFalse(ledger.digital_import_aliquots_file)

    def test_document_types_not_exported_stay_out_of_the_files(self):
        self.doc_invoice_a.export_to_digital = False
        ledger = self._create_ledger("sale", self.sale_journal)
        ledger.compute_digital_data()
        self.assertIn(self.sale_invoice, ledger.invoice_ids)
        self.assertFalse(ledger.REGDIGITAL_CV_CBTE)
        self.assertFalse(ledger.REGDIGITAL_CV_ALICUOTAS)

    def test_purchase_vat_ledger_requires_the_vendor_document(self):
        partner_without_vat = self.env["res.partner"].create(
            {
                "name": "Sin CUIT",
                "country_id": self.env.ref("base.ar").id,
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
                    price_unit=200.0,
                    product_id=self.product_iva_21,
                    tax_ids=[Command.set(self.tax_21_purchase.ids)],
                )
            ],
        )
        bill_without_vat.l10n_latam_document_number = "00001-00000999"
        bill_without_vat.action_post()

        ledger = self._create_ledger("purchase", self.purchase_journal)
        with self.assertRaisesRegex(ValidationError, "Sin CUIT"):
            ledger.compute_digital_data()

    def test_state_transitions(self):
        ledger = self._create_ledger("sale", self.sale_journal)
        self.assertEqual(ledger.state, "draft")
        ledger.action_present()
        self.assertEqual(ledger.state, "presented")
        ledger.action_cancel()
        self.assertEqual(ledger.state, "cancel")
        ledger.action_to_draft()
        self.assertEqual(ledger.state, "draft")

    def test_name_describes_type_and_period(self):
        ledger = self._create_ledger("purchase", self.purchase_journal)
        ledger.reference = "June"
        self.assertEqual(
            ledger.name, "Purchases VAT Ledger 01-06-2026 - 30-06-2026 - June"
        )

    def test_unimplemented_prorate_tax_credit_raises_a_clear_error(self):
        ledger = self._create_ledger("purchase", self.purchase_journal)
        ledger.prorate_tax_credit = True
        with self.assertRaisesRegex(ValidationError, "Crédito Fiscal Computable"):
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
                "country_id": self.env.ref("base.ar").id,
                "vat": "30-71429569-8",
                "l10n_ar_afip_responsibility_type_id": self.env.ref(
                    "l10n_ar.res_IVARI"
                ).id,
            }
        )
        number = ledger.get_partner_document_number(partner)
        self.assertEqual(number, "00000000030714295698")
        self.assertEqual(ledger.get_partner_document_code(partner), "80")

    def test_final_consumer_reports_its_own_document_type(self):
        ledger = self._create_ledger("sale", self.sale_journal)
        partner = self.env["res.partner"].create(
            {
                "name": "Consumidor con DNI",
                "country_id": self.env.ref("base.ar").id,
                "additional_identifiers": {"AR_DNI": "34654873"},
                "l10n_ar_afip_responsibility_type_id": self.env.ref(
                    "l10n_ar.res_CF"
                ).id,
            }
        )
        self.assertEqual(ledger.get_partner_document_code(partner), "96")
        self.assertEqual(
            ledger.get_partner_document_number(partner), "34654873".zfill(20)
        )

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
        self.assertEqual(
            self._create_ledger("sale", self.sale_journal)._get_aliquots(
                self.sale_invoice
            ),
            len(self.sale_invoice._get_vat()),
        )
        self.assertEqual(len(self.sale_invoice._get_vat()), 2)

    def test_pdf_report_lists_the_invoices_and_totals(self):
        ledger = self._create_ledger("sale", self.sale_journal)
        html, _content_type = self.env["ir.actions.report"]._render_qweb_html(
            "l10n_ar_ledger.l10n_ar_action_report_ledger", ledger.ids
        )
        html = html.decode()
        self.assertIn(self.sale_invoice.name, html)
        self.assertNotIn(self.other_journal_invoice.name, html)
        self.assertIn("1,792.50", html)
        report = self.env.ref("l10n_ar_ledger.l10n_ar_action_report_ledger")
        self.assertEqual(report.report_type, "qweb-pdf")
        self.assertEqual(report.paperformat_id.orientation, "Landscape")

    def test_xlsx_report_has_one_row_per_invoice(self):
        ledger = self._create_ledger("sale", self.sale_journal)
        content, content_type = self.env["ir.actions.report"]._render_xlsx(
            "l10n_ar_ledger.account_vat_ledger_xlsx", ledger.ids, {}
        )
        self.assertEqual(content_type, "xlsx")
        sheet = openpyxl.load_workbook(io.BytesIO(content)).active
        self.assertEqual(sheet.title, "IVA Ventas")
        rows = [row for row in sheet.iter_rows(min_row=5, values_only=True) if row[0]]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "ADHOC SA")
        self.assertEqual(rows[0][5], self.sale_invoice.name)
        # VAT 21% (col 10), VAT 10.5% (col 11), IIBB perception (col 13), total
        self.assertEqual(rows[0][10], 210.0)
        self.assertEqual(rows[0][11], 52.5)
        self.assertEqual(rows[0][13], 30.0)
        self.assertAlmostEqual(rows[0][19], 1792.50)
