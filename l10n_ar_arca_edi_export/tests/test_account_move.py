# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_ar.tests.common import TestArCommon


def _self_signed_cert_and_key_pem():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "test.l10n_ar_arca_edi_export")]
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


# The `_post()` of l10n_ar_arca_edi swallows the CAE request exception and logs
# it with `_logger.exception` (design decision: a rejection does not undo the
# posting). Tests going through that path need `mute_logger`, otherwise the
# ERROR in the log fails the OCA `checklog-odoo` even with 0 failed.
# Applied per method, not on the class: `mute_logger` is a function decorator,
# on a class it turns it into a callable and unittest stops discovering the
# tests ("0 tests", which is a failure, not a success).
_MUTE_EDI = mute_logger("odoo.addons.l10n_ar_arca_edi.models.account_move")


@tagged("post_install", "-at_install")
class TestAccountMoveArcaEdiExport(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_ri.l10n_ar_arca_environment = "homologacion"
        cert_pem, key_pem = _self_signed_cert_and_key_pem()
        cls.certificate = cls.env["certificate.certificate"].create(
            {
                "name": "Certificado de prueba",
                "company_id": cls.company_ri.id,
                "content": base64.b64encode(cert_pem + b"\n" + key_pem),
            }
        )
        cls.company_ri.l10n_ar_arca_certificate_id = cls.certificate

        # Test value, not the real ARCA code (which is not verified against an
        # official source in this project, see readme/ROADMAP.rst and the help
        # of res.country.l10n_ar_arca_cuit_pais).
        cls.env.ref("base.es").l10n_ar_arca_cuit_pais = "203"

        cls.export_invoice = cls._create_invoice_ar(
            journal_id=cls.sale_expo_journal_ri.id,
            partner_id=cls.res_partner_barcelona_food.id,
            invoice_line_ids=[
                cls._prepare_invoice_line(
                    price_unit=100.0, product_id=cls.product_iva_21
                )
            ],
        )

    def test_export_invoice_is_recognized_by_letter_e(self):
        self.assertEqual(
            self.export_invoice.l10n_latam_document_type_id.l10n_ar_letter, "E"
        )
        self.assertTrue(self.export_invoice.l10n_ar_arca_is_export)

    @_MUTE_EDI
    def test_missing_tipo_expo_raises_usererror_on_posting(self):
        # The invoice stays posted even on error (same decision as
        # l10n_ar_arca_edi: a rejection or error does not undo the posting);
        # the error only shows up in the log.
        with patch(
            "arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize"
        ) as mocked:
            self.export_invoice.action_post()
        mocked.assert_not_called()
        self.assertEqual(self.export_invoice.state, "posted")
        self.assertFalse(self.export_invoice.l10n_ar_arca_cae)

    @_MUTE_EDI
    def test_payload_includes_items_customer_and_cuit_pais(self):
        self.export_invoice.l10n_ar_arca_tipo_expo = "1"
        with patch("arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize"):
            self.export_invoice.action_post()

        req = self.export_invoice._l10n_ar_arca_build_fex_request()
        self.assertEqual(req.Cuit_pais_cliente, 203)
        self.assertEqual(req.Cliente, "Barcelona Food")
        self.assertTrue(req.Domicilio_cliente)
        self.assertTrue(req.Items)
        self.assertEqual(len(req.Items.Item), 1)
        self.assertAlmostEqual(req.Items.Item[0].Pro_total_item, 100.0, places=2)

    @_MUTE_EDI
    def test_missing_cuit_pais_raises_usererror(self):
        # The invoice has to be posted: without a number the payload never
        # reaches the CUIT Pais lookup and the test would pass for the wrong
        # reason (which is what happened before, when the preconditions lived
        # in this method).
        self.export_invoice.l10n_ar_arca_tipo_expo = "1"
        with patch("arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize"):
            self.export_invoice.action_post()

        self.env.ref("base.es").l10n_ar_arca_cuit_pais = False
        with (
            patch(
                "arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize"
            ) as mocked,
            self.assertRaises(UserError) as ctx,
        ):
            self.export_invoice._l10n_ar_arca_request_cae_wsfexv1()
        mocked.assert_not_called()
        self.assertIn("CUIT País", str(ctx.exception))

    @_MUTE_EDI
    def test_moncotiz_is_inverted(self):
        self.export_invoice.l10n_ar_arca_tipo_expo = "1"
        self.export_invoice.currency_id = self.env.ref("base.USD")
        self.export_invoice.invoice_currency_rate = 1000.0
        with patch("arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize"):
            self.export_invoice.action_post()
        req = self.export_invoice._l10n_ar_arca_build_fex_request()
        self.assertAlmostEqual(float(req.Moneda_ctz), 1 / 1000.0, places=6)

    @_MUTE_EDI
    def test_with_tipo_expo_calls_wsfexv1_and_stores_the_cae(self):
        self.export_invoice.l10n_ar_arca_tipo_expo = "1"
        from arcalib.wsfexv1.bindings.wsfexv1 import (
            ClsFexoutAuthorize,
            FexauthorizeResponse,
            FexresponseAuthorize,
        )

        fake_response = FexauthorizeResponse(
            FEXAuthorizeResult=FexresponseAuthorize(
                FEXResultAuth=ClsFexoutAuthorize(
                    Id=1,
                    Cuit=20111111112,
                    Cbte_tipo=19,
                    Punto_vta=2,
                    Cbte_nro=1,
                    Resultado="A",
                    Cae="70999999999999",
                    Fch_venc_Cae="20261231",
                )
            )
        )

        with patch(
            "arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize",
            return_value=fake_response,
        ) as mocked:
            self.export_invoice.action_post()

        mocked.assert_called_once()
        self.assertEqual(self.export_invoice.l10n_ar_arca_cae, "70999999999999")
        self.assertEqual(
            self.export_invoice.l10n_ar_arca_cae_due_date.isoformat(), "2026-12-31"
        )

    @_MUTE_EDI
    def test_manual_export_request_does_not_raise_valueerror(self):
        # Historical regression: the old routing filtered the export invoices
        # and called the l10n_ar_arca_edi super() on the rest, which raised
        # "Expected singleton" on an empty recordset after the CAE had already
        # been stored (and the manual button has no try/except of _post to
        # swallow it). Routing through `_l10n_ar_arca_webservice` removed that
        # entire class of bug, since there is no more super() over a subset;
        # the test stays as a guard of the manual button path.
        with patch("arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize"):
            self.export_invoice.action_post()
        self.assertFalse(self.export_invoice.l10n_ar_arca_cae)

        self.export_invoice.l10n_ar_arca_tipo_expo = "1"
        from arcalib.wsfexv1.bindings.wsfexv1 import (
            ClsFexoutAuthorize,
            FexauthorizeResponse,
            FexresponseAuthorize,
        )

        fake_response = FexauthorizeResponse(
            FEXAuthorizeResult=FexresponseAuthorize(
                FEXResultAuth=ClsFexoutAuthorize(
                    Id=1,
                    Cuit=20111111112,
                    Cbte_tipo=19,
                    Punto_vta=2,
                    Cbte_nro=1,
                    Resultado="A",
                    Cae="70888888888888",
                    Fch_venc_Cae="20261231",
                )
            )
        )
        with patch(
            "arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize",
            return_value=fake_response,
        ):
            self.export_invoice.action_l10n_ar_arca_request_cae()

        self.assertEqual(self.export_invoice.l10n_ar_arca_cae, "70888888888888")

    @_MUTE_EDI
    def test_manual_request_reraises_the_rejection(self):
        self.export_invoice.l10n_ar_arca_tipo_expo = "1"
        from arcalib.wsfexv1.bindings.wsfexv1 import (
            ClsFexoutAuthorize,
            FexauthorizeResponse,
            FexresponseAuthorize,
        )

        fake_response = FexauthorizeResponse(
            FEXAuthorizeResult=FexresponseAuthorize(
                FEXResultAuth=ClsFexoutAuthorize(
                    Id=1,
                    Cuit=20111111112,
                    Cbte_tipo=19,
                    Punto_vta=2,
                    Cbte_nro=1,
                    Resultado="R",
                    Motivos_Obs="pais destino invalido",
                )
            )
        )
        with patch(
            "arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize",
            return_value=fake_response,
        ):
            self.export_invoice.action_post()

        with (
            patch(
                "arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize",
                return_value=fake_response,
            ),
            self.assertRaises(UserError),
        ):
            self.export_invoice.action_l10n_ar_arca_request_cae()

    @_MUTE_EDI
    def test_permiso_existente_is_sent_on_goods_export(self):
        """Mandatory WSFEXv1 field for Tipo_expo = 1.

        Regression: the field exists in the binding but was never filled, so it
        serialized as absent and ARCA rejected the definitive export of goods
        for a missing mandatory field.
        """
        self.export_invoice.l10n_ar_arca_tipo_expo = "1"
        with patch("arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize"):
            self.export_invoice.action_post()

        req = self.export_invoice._l10n_ar_arca_build_fex_request()
        self.assertEqual(req.Permiso_existente, "N")

    @_MUTE_EDI
    def test_permiso_existente_is_absent_on_service_export(self):
        """ARCA does not accept the field outside the export of goods."""
        self.export_invoice.l10n_ar_arca_tipo_expo = "2"
        with patch("arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize"):
            self.export_invoice.action_post()

        req = self.export_invoice._l10n_ar_arca_build_fex_request()
        self.assertIsNone(req.Permiso_existente)

    @_MUTE_EDI
    def test_permiso_existente_yes_is_refused_with_a_clear_message(self):
        """Declaring 'S' without sending the Permisos array would be rejected.

        Better to refuse here, stating the reason, than to let ARCA return a
        generic error after a document number has been consumed.
        """
        self.export_invoice.l10n_ar_arca_tipo_expo = "1"
        self.export_invoice.l10n_ar_arca_permiso_existente = "S"
        with patch("arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize"):
            self.export_invoice.action_post()

        with self.assertRaises(UserError):
            self.export_invoice._l10n_ar_arca_build_fex_request()

    @_MUTE_EDI
    def test_export_with_tax_is_refused_before_sending(self):
        """WSFEXv1 has no field for tax: only items and total.

        Regression: Imp_total was `amount_total` (with tax) while the items
        carried no tax, so the total/detail identity ARCA validates did not
        hold. Now the total comes from the items and the mismatch is refused
        here, with a message naming what is left over.
        """
        self.tax_perc_iibb.amount = 3.0
        invoice = self._create_invoice_ar(
            journal_id=self.sale_expo_journal_ri.id,
            partner_id=self.res_partner_barcelona_food.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=100.0, product_id=self.product_iva_21
                )
            ],
        )
        # ADDS the perception to the taxes the line already has, instead of
        # replacing them: the core requires exactly one tax of the VAT group
        # per line on an Argentine invoice, and swapping the set would break on
        # posting for that reason, not for what this test wants to exercise.
        invoice.invoice_line_ids[0].tax_ids = [Command.link(self.tax_perc_iibb.id)]
        invoice.l10n_ar_arca_tipo_expo = "1"
        with patch("arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize"):
            invoice.action_post()

        self.assertNotEqual(invoice.amount_total, invoice.amount_untaxed)
        with self.assertRaises(UserError):
            invoice._l10n_ar_arca_build_fex_request()

    @_MUTE_EDI
    def test_items_skip_a_technical_line_without_unit_of_measure(self):
        """Early payment discount and cash rounding lines reach
        `_get_rounded_base_and_tax_lines()` without a unit of measure.

        Regression: the loop demanded an AFIP UoM code on every base line and
        blew up on those. The technical line is synthetic here on purpose:
        building a real cash rounding scenario would drag in company
        configuration irrelevant to what is under test, which is the `continue`.
        """
        self.export_invoice.l10n_ar_arca_tipo_expo = "1"
        with patch("arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize"):
            self.export_invoice.action_post()

        original = type(self.export_invoice)._get_rounded_base_and_tax_lines

        def _with_special_line(move, **kwargs):
            base_lines, tax_lines = original(move, **kwargs)
            fake = dict(base_lines[0])
            fake["special_type"] = "cash_rounding"
            fake["product_uom_id"] = move.env["uom.uom"]
            return base_lines + [fake], tax_lines

        with patch.object(
            type(self.export_invoice),
            "_get_rounded_base_and_tax_lines",
            _with_special_line,
        ):
            req = self.export_invoice._l10n_ar_arca_build_fex_request()

        # The technical line did not become an item, and the total still holds.
        self.assertEqual(len(req.Items.Item), 1)
        self.assertAlmostEqual(
            float(req.Imp_total), self.export_invoice.amount_total, places=2
        )

    @_MUTE_EDI
    def test_routing_picks_wsfexv1_from_letter_e(self):
        """Dispatch goes by webservice key, not by partial override.

        An export invoice resolves to `wsfexv1`; anything else keeps falling
        through to `super()`, which returns `wsfev1`. That is what allows a
        third webservice to be added without touching the first two.
        """
        self.export_invoice.l10n_ar_arca_tipo_expo = "1"
        with patch("arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize"):
            self.export_invoice.action_post()

        self.assertEqual(self.export_invoice._l10n_ar_arca_webservice(), "wsfexv1")

        # No posting needed: `_l10n_ar_arca_webservice` only looks at the
        # letter of the document type, already resolved on the draft.
        domestic_journal = self._create_journal(
            "wsfe",
            data={
                "l10n_ar_afip_pos_system": "RLI_RLM",
                "l10n_ar_afip_pos_number": "9",
            },
        )
        domestic = self._create_invoice_ar(
            journal_id=domestic_journal.id,
            partner_id=self.partner_cf.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=100.0, product_id=self.product_iva_21
                )
            ],
        )
        self.assertFalse(domestic.l10n_ar_arca_is_export)
        self.assertEqual(domestic._l10n_ar_arca_webservice(), "wsfev1")
