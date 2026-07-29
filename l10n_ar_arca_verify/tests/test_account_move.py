# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_ar.tests.common import TestArCommon


def _self_signed_cert_and_key_pem():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "test.l10n_ar_arca_verify")]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    return cert.public_bytes(serialization.Encoding.PEM), key_pem


@tagged("post_install", "-at_install")
class TestAccountMoveArcaVerify(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_ri.l10n_ar_arca_environment = "homologacion"
        cert_pem, key_pem = _self_signed_cert_and_key_pem()
        cls.certificate = cls.env["certificate.certificate"].create(
            {
                "name": "Certificado de teste",
                "company_id": cls.company_ri.id,
                "content": base64.b64encode(cert_pem + b"\n" + key_pem),
            }
        )
        cls.company_ri.l10n_ar_arca_certificate_id = cls.certificate

        cls.vendor_bill = cls._create_invoice_ar(
            move_type="in_invoice",
            partner_id=cls.res_partner_adhoc.id,
            invoice_line_ids=[
                cls._prepare_invoice_line(
                    price_unit=100.0, product_id=cls.product_iva_21
                )
            ],
        )
        # A vendor bill in Argentina requires a manual document number
        # (l10n_ar/models/account_move.py:_is_manual_document_number).
        cls.vendor_bill.l10n_latam_document_number = "00001-00000123"
        cls.vendor_bill.action_post()

    def test_missing_vendor_cae_raises_usererror_without_calling_arca(self):
        with (
            patch(
                "arcalib.transmissao.wscdc.TransmissaoWSCDC.comprobante_constatar"
            ) as mocked,
            self.assertRaises(UserError),
        ):
            self.vendor_bill.action_l10n_ar_arca_verify_comprobante()
        mocked.assert_not_called()

    def test_verifies_and_stores_the_result(self):
        self.vendor_bill.l10n_ar_arca_verify_vendor_cae = "70123456789012"
        from arcalib.wscdc.bindings.wscdc import (
            ArrayOfObs,
            CmpResponse,
            ComprobanteConstatarResponse,
            Obs,
        )

        fake_response = ComprobanteConstatarResponse(
            ComprobanteConstatarResult=CmpResponse(
                Resultado="OK",
                Observaciones=ArrayOfObs(Obs=[Obs(Code=1, Msg="observacao teste")]),
            )
        )

        with patch(
            "arcalib.transmissao.wscdc.TransmissaoWSCDC.comprobante_constatar",
            return_value=fake_response,
        ) as mocked:
            self.vendor_bill.action_l10n_ar_arca_verify_comprobante()

        mocked.assert_called_once()
        cmp_datos = mocked.call_args.args[0]
        # Literal expected value, not a re-run of the production
        # normalization (regression: res_partner_adhoc.vat = "30714295698",
        # without separators, but the code still has to go through the
        # sanitize helper rather than a raw int(vat)).
        self.assertEqual(cmp_datos.CuitEmisor, 30714295698)
        self.assertEqual(
            cmp_datos.CbteTipo, int(self.vendor_bill.l10n_latam_document_type_id.code)
        )
        self.assertEqual(cmp_datos.PtoVta, 1)
        self.assertEqual(cmp_datos.CbteNro, 123)
        # The receptor of the document is the company itself, not the vendor.
        self.assertEqual(
            cmp_datos.DocNroReceptor,
            str(self.company_ri.partner_id._get_id_number_sanitize()),
        )
        self.assertEqual(self.vendor_bill.l10n_ar_arca_verify_result, "OK")
        self.assertIn(
            "observacao teste", self.vendor_bill.l10n_ar_arca_verify_observations
        )

    def test_customer_invoice_cannot_be_verified_without_calling_arca(self):
        sale_invoice = self._create_invoice_ar(
            partner_id=self.res_partner_adhoc.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=50.0, product_id=self.product_iva_21
                )
            ],
        )
        sale_invoice.l10n_ar_arca_verify_vendor_cae = "70123456789012"
        with (
            patch(
                "arcalib.transmissao.wscdc.TransmissaoWSCDC.comprobante_constatar"
            ) as mocked,
            self.assertRaises(UserError),
        ):
            sale_invoice.action_l10n_ar_arca_verify_comprobante()
        mocked.assert_not_called()
