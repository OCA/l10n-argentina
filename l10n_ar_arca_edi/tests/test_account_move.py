# Copyright 2026 Leonobitech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import datetime
import json

from unittest.mock import patch, MagicMock

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import ArcaEdiTestCommon


@tagged("post_install", "-at_install")
class TestAccountMoveArcaDocType(ArcaEdiTestCommon):
    """Test _get_arca_doc_type_code() validation."""

    def _create_move(self, doc_type, partner=None):
        """Helper: create a minimal account.move with the given doc type."""
        return self.env["account.move"].with_company(self.company).create({
            "move_type": "out_invoice",
            "journal_id": self.journal.id,
            "partner_id": (partner or self.partner_cf).id,
            "invoice_date": datetime.date(2026, 3, 15),
            "l10n_latam_document_type_id": doc_type.id,
        })

    def test_get_arca_doc_type_code_factura_c(self):
        """Factura C (code 11) is a supported ARCA doc type."""
        move = self._create_move(self.doc_type_fc)
        code = move._get_arca_doc_type_code()
        self.assertEqual(code, 11)

    def test_get_arca_doc_type_code_factura_a(self):
        """Factura A (code 1) is a supported ARCA doc type."""
        move = self._create_move(self.doc_type_fa)
        code = move._get_arca_doc_type_code()
        self.assertEqual(code, 1)

    def test_get_arca_doc_type_code_nota_credito_c(self):
        """Nota de Credito C (code 13) is a supported ARCA doc type."""
        move = self.env["account.move"].with_company(self.company).create({
            "move_type": "out_refund",
            "journal_id": self.journal.id,
            "partner_id": self.partner_cf.id,
            "invoice_date": datetime.date(2026, 3, 15),
            "l10n_latam_document_type_id": self.doc_type_nc_c.id,
        })
        code = move._get_arca_doc_type_code()
        self.assertEqual(code, 13)

    def test_get_arca_doc_type_code_unsupported_raises(self):
        """Unsupported doc type code raises UserError."""
        move = self._create_move(self.doc_type_unsupported)
        with self.assertRaises(UserError):
            move._get_arca_doc_type_code()

    def test_get_arca_doc_type_code_no_doc_type_raises(self):
        """Missing document type raises UserError."""
        move = self.env["account.move"].with_company(self.company).create({
            "move_type": "out_invoice",
            "journal_id": self.journal.id,
            "partner_id": self.partner_cf.id,
            "invoice_date": datetime.date(2026, 3, 15),
        })
        # Force-clear the document type (l10n_ar may auto-assign)
        move.l10n_latam_document_type_id = False
        with self.assertRaises(UserError):
            move._get_arca_doc_type_code()


@tagged("post_install", "-at_install")
class TestAccountMoveArcaConceptType(ArcaEdiTestCommon):
    """Test _get_arca_concept_type() (1=products, 2=services, 3=both)."""

    def _create_product(self, product_type):
        return self.env["product.product"].create({
            "name": f"Test {product_type}",
            "type": product_type,
        })

    def _create_move_with_lines(self, product_types):
        """Create a move with invoice lines for given product types."""
        move = self.env["account.move"].with_company(self.company).create({
            "move_type": "out_invoice",
            "journal_id": self.journal.id,
            "partner_id": self.partner_cf.id,
            "invoice_date": datetime.date(2026, 3, 15),
            "l10n_latam_document_type_id": self.doc_type_fc.id,
            "invoice_line_ids": [
                Command.create({
                    "name": f"Line {i}",
                    "product_id": self._create_product(pt).id,
                    "account_id": self.account_revenue.id,
                    "quantity": 1,
                    "price_unit": 100.0,
                })
                for i, pt in enumerate(product_types)
            ],
        })
        return move

    def test_concept_products_only(self):
        """Only consumable products -> concept 1."""
        move = self._create_move_with_lines(["consu"])
        self.assertEqual(move._get_arca_concept_type(), 1)

    def test_concept_services_only(self):
        """Only services -> concept 2."""
        move = self._create_move_with_lines(["service"])
        self.assertEqual(move._get_arca_concept_type(), 2)

    def test_concept_both(self):
        """Mix of products and services -> concept 3."""
        move = self._create_move_with_lines(["consu", "service"])
        self.assertEqual(move._get_arca_concept_type(), 3)

    def test_concept_no_products_defaults_to_1(self):
        """No products at all (lines without product) -> concept 1 (default)."""
        move = self.env["account.move"].with_company(self.company).create({
            "move_type": "out_invoice",
            "journal_id": self.journal.id,
            "partner_id": self.partner_cf.id,
            "invoice_date": datetime.date(2026, 3, 15),
            "l10n_latam_document_type_id": self.doc_type_fc.id,
            "invoice_line_ids": [
                Command.create({
                    "name": "Generic line",
                    "account_id": self.account_revenue.id,
                    "quantity": 1,
                    "price_unit": 50.0,
                })
            ],
        })
        self.assertEqual(move._get_arca_concept_type(), 1)


@tagged("post_install", "-at_install")
class TestAccountMoveArcaCustomerDoc(ArcaEdiTestCommon):
    """Test _get_arca_customer_doc() for different partner configurations."""

    def _create_move(self, partner):
        return self.env["account.move"].with_company(self.company).create({
            "move_type": "out_invoice",
            "journal_id": self.journal.id,
            "partner_id": partner.id,
            "invoice_date": datetime.date(2026, 3, 15),
            "l10n_latam_document_type_id": self.doc_type_fc.id,
        })

    def test_customer_doc_consumidor_final(self):
        """Consumidor Final (no VAT) -> doc_type=99, doc_number=0."""
        move = self._create_move(self.partner_cf)
        partner = move.partner_id.commercial_partner_id
        doc_type, doc_number = move._get_arca_customer_doc(partner)
        self.assertEqual(doc_type, 99)
        self.assertEqual(doc_number, 0)

    def test_customer_doc_cuit(self):
        """Partner with CUIT -> doc_type=80, doc_number=numeric CUIT."""
        move = self._create_move(self.partner_ri)
        partner = move.partner_id.commercial_partner_id
        doc_type, doc_number = move._get_arca_customer_doc(partner)
        self.assertEqual(doc_type, 80)
        # "30-71234567-9" -> 30712345679
        self.assertEqual(doc_number, 30712345679)

    def test_customer_doc_dni(self):
        """Partner with DNI -> doc_type=96, doc_number=numeric DNI."""
        move = self._create_move(self.partner_dni)
        partner = move.partner_id.commercial_partner_id
        doc_type, doc_number = move._get_arca_customer_doc(partner)
        self.assertEqual(doc_type, 96)
        self.assertEqual(doc_number, 12345678)


@tagged("post_install", "-at_install")
class TestAccountMoveArcaBarcode(ArcaEdiTestCommon):
    """Test _build_arca_barcode() with known values."""

    def _create_move(self):
        return self.env["account.move"].with_company(self.company).create({
            "move_type": "out_invoice",
            "journal_id": self.journal.id,
            "partner_id": self.partner_cf.id,
            "invoice_date": datetime.date(2026, 3, 15),
            "l10n_latam_document_type_id": self.doc_type_fc.id,
        })

    def test_build_barcode_known_values(self):
        """Barcode built with known CUIT, doc type, POS, CAE, date."""
        move = self._create_move()
        cae_result = {
            "cae": "74291378046073",
            "cae_due_date": "20260325",
        }
        barcode = move._build_arca_barcode(
            self.certificate, 11, self.journal, cae_result
        )

        # Expected structure:
        # CUIT (11) + CbteTipo (3) + PtoVta (5) + CAE (14) + FchVto (8) + check (1)
        self.assertTrue(barcode)
        self.assertEqual(len(barcode), 42)  # 11+3+5+14+8+1

        # Verify components
        self.assertTrue(barcode.startswith("20293188204"))  # CUIT without dashes
        self.assertIn("011", barcode[11:14])  # CbteTipo 011
        self.assertIn("00003", barcode[14:19])  # PtoVta 00003
        self.assertIn("74291378046073", barcode[19:33])  # CAE
        self.assertIn("20260325", barcode[33:41])  # FchVto

    def test_build_barcode_check_digit(self):
        """Verify the mod-10 check digit calculation."""
        move = self._create_move()
        cae_result = {
            "cae": "74291378046073",
            "cae_due_date": "20260325",
        }
        barcode = move._build_arca_barcode(
            self.certificate, 11, self.journal, cae_result
        )

        # Recalculate check digit manually
        data = barcode[:-1]
        odd_sum = sum(int(d) for d in data[::2])
        even_sum = sum(int(d) for d in data[1::2])
        total = odd_sum * 3 + even_sum
        expected_check = (10 - (total % 10)) % 10
        self.assertEqual(int(barcode[-1]), expected_check)

    def test_build_barcode_no_cae_returns_false(self):
        """Missing CAE in result -> returns False."""
        move = self._create_move()
        result = move._build_arca_barcode(
            self.certificate, 11, self.journal, {"cae": None, "cae_due_date": None}
        )
        self.assertFalse(result)

    def test_build_barcode_empty_cae_returns_false(self):
        """Empty CAE string -> returns False."""
        move = self._create_move()
        result = move._build_arca_barcode(
            self.certificate, 11, self.journal, {"cae": "", "cae_due_date": ""}
        )
        self.assertFalse(result)


@tagged("post_install", "-at_install")
class TestAccountMoveArcaQrCode(ArcaEdiTestCommon):
    """Test _build_arca_qr_code() URL generation."""

    def _create_move(self, partner=None):
        return self.env["account.move"].with_company(self.company).create({
            "move_type": "out_invoice",
            "journal_id": self.journal.id,
            "partner_id": (partner or self.partner_cf).id,
            "invoice_date": datetime.date(2026, 3, 15),
            "l10n_latam_document_type_id": self.doc_type_fc.id,
            "invoice_line_ids": [
                Command.create({
                    "name": "Test Service",
                    "account_id": self.account_revenue.id,
                    "quantity": 1,
                    "price_unit": 1500.00,
                })
            ],
        })

    def test_build_qr_code_url_structure(self):
        """QR URL starts with AFIP domain and contains base64 payload."""
        move = self._create_move()
        cae_result = {
            "cae": "74291378046073",
            "cae_due_date": "20260325",
        }
        url = move._build_arca_qr_code(
            self.certificate, 11, self.journal, 1, cae_result
        )
        self.assertTrue(url)
        self.assertTrue(url.startswith("https://www.afip.gob.ar/fe/qr/?p="))

    def test_build_qr_code_payload_content(self):
        """Decoded QR payload contains correct invoice data."""
        move = self._create_move()
        cae_result = {
            "cae": "74291378046073",
            "cae_due_date": "20260325",
        }
        url = move._build_arca_qr_code(
            self.certificate, 11, self.journal, 42, cae_result
        )

        # Extract and decode the base64 payload
        encoded = url.split("?p=")[1]
        payload = json.loads(base64.b64decode(encoded).decode("utf-8"))

        self.assertEqual(payload["ver"], 1)
        self.assertEqual(payload["fecha"], "2026-03-15")
        self.assertEqual(payload["cuit"], 20293188204)
        self.assertEqual(payload["ptoVta"], 3)
        self.assertEqual(payload["tipoCmp"], 11)
        self.assertEqual(payload["nroCmp"], 42)
        self.assertEqual(payload["moneda"], "PES")
        self.assertEqual(payload["ctz"], 1)
        self.assertEqual(payload["tipoCodAut"], "E")
        self.assertEqual(payload["codAut"], 74291378046073)

    def test_build_qr_code_consumidor_final_doc(self):
        """QR payload for Consumidor Final has tipoDocRec=99, nroDocRec=0."""
        move = self._create_move(self.partner_cf)
        cae_result = {
            "cae": "74291378046073",
            "cae_due_date": "20260325",
        }
        url = move._build_arca_qr_code(
            self.certificate, 11, self.journal, 1, cae_result
        )
        encoded = url.split("?p=")[1]
        payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
        self.assertEqual(payload["tipoDocRec"], 99)
        self.assertEqual(payload["nroDocRec"], 0)

    def test_build_qr_code_no_cae_returns_false(self):
        """Missing CAE -> returns False."""
        move = self._create_move()
        result = move._build_arca_qr_code(
            self.certificate, 11, self.journal, 1,
            {"cae": None, "cae_due_date": None}
        )
        self.assertFalse(result)


@tagged("post_install", "-at_install")
class TestAccountMoveArcaActions(ArcaEdiTestCommon):
    """Test action_verify_arca / action_request_cae guard conditions."""

    def _create_move(self, cae=False):
        move = self.env["account.move"].with_company(self.company).create({
            "move_type": "out_invoice",
            "journal_id": self.journal.id,
            "partner_id": self.partner_cf.id,
            "invoice_date": datetime.date(2026, 3, 15),
            "l10n_latam_document_type_id": self.doc_type_fc.id,
        })
        if cae:
            move.l10n_ar_arca_cae = cae
        return move

    def test_verify_arca_no_cae_raises(self):
        """action_verify_arca raises UserError when invoice has no CAE."""
        move = self._create_move()
        with self.assertRaises(UserError):
            move.action_verify_arca()

    def test_verify_arca_no_certificate_raises(self):
        """action_verify_arca raises UserError when no certificate configured."""
        move = self._create_move(cae="74291378046073")
        # Remove certificate from company
        self.company.l10n_ar_arca_certificate_id = False
        with self.assertRaises(UserError):
            move.action_verify_arca()

    def test_request_cae_already_has_cae_raises(self):
        """action_request_cae raises UserError when CAE already exists."""
        move = self._create_move(cae="74291378046073")
        with self.assertRaises(UserError):
            move.action_request_cae()


@tagged("post_install", "-at_install")
class TestAccountMoveArcaPrepareData(ArcaEdiTestCommon):
    """Test _prepare_arca_invoice_data() output structure."""

    def _create_move_with_line(self, partner=None, doc_type=None, product_type="service"):
        product = self.env["product.product"].create({
            "name": "Test Product",
            "type": product_type,
        })
        move = self.env["account.move"].with_company(self.company).create({
            "move_type": "out_invoice",
            "journal_id": self.journal.id,
            "partner_id": (partner or self.partner_cf).id,
            "invoice_date": datetime.date(2026, 3, 15),
            "l10n_latam_document_type_id": (doc_type or self.doc_type_fc).id,
            "invoice_line_ids": [
                Command.create({
                    "name": "Test Line",
                    "product_id": product.id,
                    "account_id": self.account_revenue.id,
                    "quantity": 2,
                    "price_unit": 500.00,
                })
            ],
        })
        return move

    def test_prepare_data_factura_c_structure(self):
        """Factura C: all amount in net_taxed, IVA totals are 0."""
        move = self._create_move_with_line()
        data = move._prepare_arca_invoice_data(
            self.certificate, self.journal, 11, 1
        )

        # Required keys present
        self.assertIn("pos_number", data)
        self.assertIn("doc_type_code", data)
        self.assertIn("concept", data)
        self.assertIn("customer_doc_type", data)
        self.assertIn("customer_doc_number", data)
        self.assertIn("invoice_number", data)
        self.assertIn("date", data)
        self.assertIn("total", data)
        self.assertIn("net_untaxed", data)
        self.assertIn("net_taxed", data)
        self.assertIn("tax_exempt", data)
        self.assertIn("iva_total", data)
        self.assertIn("iva_lines", data)

        # Factura C specifics
        self.assertEqual(data["doc_type_code"], 11)
        self.assertEqual(data["pos_number"], 3)
        self.assertEqual(data["invoice_number"], 1)
        self.assertEqual(data["date"], "20260315")

        # Factura C: iva_total must be 0, iva_lines empty
        self.assertEqual(data["iva_total"], 0)
        self.assertEqual(data["iva_lines"], [])
        self.assertEqual(data["tax_exempt"], 0)

        # net_taxed == total for Factura C
        self.assertEqual(data["net_taxed"], data["total"])

    def test_prepare_data_service_includes_service_dates(self):
        """Service concept (2) includes service_date_from/to and payment_due_date."""
        move = self._create_move_with_line(product_type="service")
        data = move._prepare_arca_invoice_data(
            self.certificate, self.journal, 11, 1
        )
        # Concept should be 2 (services)
        self.assertEqual(data["concept"], 2)
        self.assertIn("service_date_from", data)
        self.assertIn("service_date_to", data)
        self.assertIn("payment_due_date", data)
        self.assertEqual(data["service_date_from"], "20260315")
        self.assertEqual(data["service_date_to"], "20260315")

    def test_prepare_data_product_no_service_dates(self):
        """Product concept (1) does NOT include service dates."""
        move = self._create_move_with_line(product_type="consu")
        data = move._prepare_arca_invoice_data(
            self.certificate, self.journal, 11, 1
        )
        self.assertEqual(data["concept"], 1)
        self.assertNotIn("service_date_from", data)
        self.assertNotIn("service_date_to", data)

    def test_prepare_data_consumidor_final_doc(self):
        """Consumidor Final partner -> customer_doc_type=99, number=0."""
        move = self._create_move_with_line(partner=self.partner_cf)
        data = move._prepare_arca_invoice_data(
            self.certificate, self.journal, 11, 1
        )
        self.assertEqual(data["customer_doc_type"], 99)
        self.assertEqual(data["customer_doc_number"], 0)

    def test_prepare_data_ri_partner_cuit(self):
        """RI partner -> customer_doc_type=80, customer_doc_number=CUIT digits."""
        move = self._create_move_with_line(partner=self.partner_ri)
        data = move._prepare_arca_invoice_data(
            self.certificate, self.journal, 11, 1
        )
        self.assertEqual(data["customer_doc_type"], 80)
        self.assertEqual(data["customer_doc_number"], 30712345679)

    def test_prepare_data_customer_iva_condition(self):
        """RI partner maps to customer_iva_condition=1 (RG 5616)."""
        move = self._create_move_with_line(partner=self.partner_ri)
        data = move._prepare_arca_invoice_data(
            self.certificate, self.journal, 11, 1
        )
        self.assertIn("customer_iva_condition", data)
        self.assertEqual(data["customer_iva_condition"], 1)

    def test_prepare_data_cf_customer_iva_condition(self):
        """Consumidor Final maps to customer_iva_condition=5."""
        move = self._create_move_with_line(partner=self.partner_cf)
        data = move._prepare_arca_invoice_data(
            self.certificate, self.journal, 11, 1
        )
        self.assertIn("customer_iva_condition", data)
        self.assertEqual(data["customer_iva_condition"], 5)
