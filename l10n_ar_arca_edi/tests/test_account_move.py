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
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test.l10n_ar_arca_edi")])
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


# The `_post()` of this module swallows the CAE request exception and logs it
# with `_logger.exception` (design decision: a rejection does not undo the
# posting). Tests going through that path need `mute_logger`, otherwise the
# ERROR in the log fails the OCA `checklog-odoo` even with 0 failed.
# Applied per method, not on the class: `mute_logger` is a function decorator,
# on a class it turns it into a callable and unittest stops discovering the
# tests ("0 tests", which is a failure, not a success).
_MUTE_EDI = mute_logger("odoo.addons.l10n_ar_arca_edi.models.account_move")


@tagged("post_install", "-at_install")
class TestAccountMoveArcaEdi(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
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

        cls.journal_arca = cls._create_journal(
            "wsfe",
            data={
                "l10n_ar_afip_pos_system": "RLI_RLM",
                "l10n_ar_afip_pos_number": "3",
            },
        )

    def _create_factura_b(self):
        return self._create_invoice_ar(
            journal_id=self.journal_arca.id,
            partner_id=self.partner_cf.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_iva_21, price_unit=100.0
                )
            ],
        )

    def _fake_fecae_response(self, resultado="A", cae="70123456789012", obs=None):
        from arcalib.wsfev1.bindings.wsfev1 import (
            ArrayOfFecaedetResponse,
            FecaecabResponse,
            FecaedetResponse,
            FecaesolicitarResponse,
        )

        det = FecaedetResponse(
            Concepto=1,
            DocTipo=99,
            DocNro=0,
            CbteDesde=1,
            CbteHasta=1,
            Resultado=resultado,
            CAE=cae if resultado == "A" else None,
            CAEFchVto="20261231" if resultado == "A" else None,
        )
        if obs:
            from arcalib.wsfev1.bindings.wsfev1 import ArrayOfObs, Obs

            det.Observaciones = ArrayOfObs(Obs=[Obs(Code=10001, Msg=obs)])

        from arcalib.wsfev1.bindings.wsfev1 import Fecaeresponse

        return FecaesolicitarResponse(
            FECAESolicitarResult=Fecaeresponse(
                FeCabResp=FecaecabResponse(
                    Cuit=int(self.company_ri.vat),
                    PtoVta=self.journal_arca.l10n_ar_afip_pos_number,
                    CbteTipo=6,
                    CantReg=1,
                ),
                FeDetResp=ArrayOfFecaedetResponse(FECAEDetResponse=[det]),
            )
        )

    def test_posting_requests_the_cae_and_stores_it_on_success(self):
        invoice = self._create_factura_b()
        fake_response = self._fake_fecae_response(resultado="A")

        with patch(
            "arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar",
            return_value=fake_response,
        ) as mocked:
            invoice.action_post()

        mocked.assert_called_once()
        # Regression: the previous test only checked that the method was
        # called, never the content of the payload sent.
        det = mocked.call_args.args[0].FeDetReq.FECAEDetRequest[0]
        self.assertAlmostEqual(det.ImpTotal, invoice.amount_total, places=2)
        self.assertAlmostEqual(det.ImpNeto, 100.0, places=2)
        self.assertAlmostEqual(det.ImpIVA, 21.0, places=2)
        self.assertAlmostEqual(det.ImpTotConc, 0.0, places=2)
        self.assertAlmostEqual(det.ImpTrib, 0.0, places=2)

        self.assertEqual(invoice.state, "posted")
        self.assertEqual(invoice.l10n_ar_arca_cae, "70123456789012")
        self.assertEqual(invoice.l10n_ar_arca_cae_due_date.isoformat(), "2026-12-31")
        self.assertEqual(invoice.l10n_ar_arca_result, "A")

    @_MUTE_EDI
    def test_payload_with_perception_splits_impneto_and_imptrib(self):
        # The core `tax_perc_iibb` fixture comes with a 0% rate (the real one
        # varies per jurisdiction and the core does not risk a number); a rate
        # is forced here only so the test can check the aggregation, not the
        # legal rate of any particular jurisdiction.
        self.tax_perc_iibb.amount = 3.0
        invoice = self._create_invoice_ar(
            journal_id=self.journal_arca.id,
            partner_id=self.partner_cf.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_iva_105_perc,
                    price_unit=1000.0,
                    tax_ids=[Command.set([self.tax_10_5.id, self.tax_perc_iibb.id])],
                )
            ],
        )
        with patch("arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar"):
            invoice.action_post()

        req = invoice._l10n_ar_arca_build_fecae_request()
        det = req.FeDetReq.FECAEDetRequest[0]
        # ImpNeto (the VAT base) must not include the IIBB perception.
        self.assertAlmostEqual(det.ImpNeto, 1000.0, places=2)
        self.assertAlmostEqual(det.ImpIVA, 105.0, places=2)
        # ImpTrib has to reflect the IIBB perception (regression: the previous
        # manual sum skipped the group and zeroed this out).
        self.assertAlmostEqual(det.ImpTrib, 30.0, places=2)
        self.assertTrue(det.Tributos)
        self.assertEqual(len(det.Tributos.Tributo), 1)
        tributo = det.Tributos.Tributo[0]
        self.assertAlmostEqual(tributo.Importe, det.ImpTrib, places=2)
        self.assertAlmostEqual(tributo.BaseImp, 1000.0, places=2)

    @_MUTE_EDI
    def test_credit_note_sends_cbtes_asoc(self):
        invoice = self._create_factura_b()
        with patch("arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar"):
            invoice.action_post()

        credit_note_wizard = (
            self.env["account.move.reversal"]
            .with_context(active_ids=invoice.ids, active_model="account.move")
            .create({"reason": "prueba", "journal_id": invoice.journal_id.id})
        )
        credit_note_wizard.refund_moves()
        credit_note = invoice.reversal_move_ids
        with patch("arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar"):
            credit_note.action_post()

        req = credit_note._l10n_ar_arca_build_fecae_request()
        det = req.FeDetReq.FECAEDetRequest[0]
        self.assertTrue(det.CbtesAsoc)
        cbte_asoc = det.CbtesAsoc.CbteAsoc[0]
        self.assertEqual(cbte_asoc.Tipo, int(invoice.l10n_latam_document_type_id.code))
        self.assertEqual(cbte_asoc.PtoVta, self.journal_arca.l10n_ar_afip_pos_number)

    @_MUTE_EDI
    def test_moncotiz_is_inverted_for_a_foreign_currency(self):
        foreign_currency = self.env.ref("base.USD")
        if foreign_currency == self.company_ri.currency_id:
            foreign_currency = self.env.ref("base.EUR")
        invoice = self._create_invoice_ar(
            journal_id=self.journal_arca.id,
            partner_id=self.partner_cf.id,
            currency_id=foreign_currency.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_iva_21, price_unit=100.0
                )
            ],
        )
        invoice.invoice_currency_rate = 1000.0
        with patch("arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar"):
            invoice.action_post()

        req = invoice._l10n_ar_arca_build_fecae_request()
        det = req.FeDetReq.FECAEDetRequest[0]
        # ARCA wants pesos per foreign unit: the inverse of what Odoo stores
        # in invoice_currency_rate (foreign currency per peso).
        self.assertAlmostEqual(det.MonCotiz, 1 / 1000.0, places=6)

    @_MUTE_EDI
    def test_rejection_keeps_the_invoice_posted_without_cae(self):
        invoice = self._create_factura_b()
        fake_response = self._fake_fecae_response(
            resultado="R", obs="CUIT del receptor no valido"
        )

        with patch(
            "arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar",
            return_value=fake_response,
        ):
            invoice.action_post()

        # Decision recorded in the module (see `_post`): a rejection does not
        # undo the posting, the invoice stays pending a resend.
        self.assertEqual(invoice.state, "posted")
        self.assertFalse(invoice.l10n_ar_arca_cae)
        self.assertEqual(invoice.l10n_ar_arca_result, "R")
        self.assertIn("CUIT del receptor no valido", invoice.l10n_ar_arca_observations)

    @_MUTE_EDI
    def test_manual_request_reraises_the_arca_error(self):
        invoice = self._create_factura_b()
        fake_response = self._fake_fecae_response(resultado="R", obs="erro qualquer")

        with patch(
            "arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar",
            return_value=fake_response,
        ):
            invoice.action_post()  # stays posted without CAE (see test above)

        with (
            patch(
                "arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar",
                return_value=fake_response,
            ),
            self.assertRaises(UserError),
        ):
            invoice.action_l10n_ar_arca_request_cae()

    @_MUTE_EDI
    def test_build_request_maps_the_core_amounts(self):
        invoice = self._create_factura_b()
        # The number (l10n_latam_document_number) only exists after posting.
        with patch("arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar"):
            invoice.action_post()

        req = invoice._l10n_ar_arca_build_fecae_request()

        det = req.FeDetReq.FECAEDetRequest[0]
        self.assertEqual(req.FeCabReq.PtoVta, 3)
        self.assertEqual(
            req.FeCabReq.CbteTipo, int(invoice.l10n_latam_document_type_id.code)
        )
        self.assertAlmostEqual(det.ImpTotal, invoice.amount_total, places=2)
        self.assertTrue(det.Iva)
        # The AFIP rate code comes from the core itself
        # (tax_group_id.l10n_ar_vat_afip_code), not guessed: this only checks
        # that it matches what the core computed through _get_vat().
        expected_vat = invoice._get_vat()
        self.assertEqual(det.Iva.AlicIva[0].Id, int(expected_vat[0]["Id"]))
        self.assertAlmostEqual(
            det.Iva.AlicIva[0].Importe, expected_vat[0]["Importe"], places=2
        )

    def _create_service_product(self):
        return self.env["product.product"].create(
            {
                "name": "Servicio de consultoría",
                "type": "service",
                "taxes_id": [Command.set([self.tax_21.id])],
            }
        )

    @_MUTE_EDI
    def test_service_invoice_sends_fchvtopago(self):
        """ARCA requires the payment due date on a service invoice.

        Regression: the payload filled FchServDesde/FchServHasta but never
        FchVtoPago, so every service invoice was rejected for a missing
        mandatory field.
        """
        invoice = self._create_invoice_ar(
            journal_id=self.journal_arca.id,
            partner_id=self.partner_cf.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self._create_service_product(), price_unit=500.0
                )
            ],
        )
        with patch("arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar"):
            invoice.action_post()

        self.assertEqual(invoice.l10n_ar_afip_concept, "2")
        det = invoice._l10n_ar_arca_build_fecae_request().FeDetReq.FECAEDetRequest[0]
        self.assertTrue(det.FchServDesde)
        self.assertTrue(
            det.FchVtoPago,
            "a service invoice (Concepto 2) must report FchVtoPago",
        )
        self.assertEqual(det.FchVtoPago, invoice.invoice_date_due.strftime("%Y%m%d"))

    @_MUTE_EDI
    def test_product_invoice_does_not_send_fchvtopago(self):
        """The field only applies to services: sending it on Concepto 1 is wrong."""
        invoice = self._create_factura_b()
        with patch("arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar"):
            invoice.action_post()

        self.assertEqual(invoice.l10n_ar_afip_concept, "1")
        det = invoice._l10n_ar_arca_build_fecae_request().FeDetReq.FECAEDetRequest[0]
        self.assertIsNone(det.FchVtoPago)

    @_MUTE_EDI
    def test_reversible_code_credit_note_sends_negative_amounts(self):
        """ARCA identity: ImpTotal = ImpTotConc+ImpNeto+ImpOpEx+ImpTrib+ImpIVA.

        Regression: ImpTotal came from `amount_total`, which is always
        positive, while the core flips the sign of the parts on a credit note
        whose code serves both as invoice and as note. The identity did not
        hold and ARCA rejected the document.
        """
        invoice = self._create_factura_b()
        with patch("arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar"):
            invoice.action_post()

        wizard = (
            self.env["account.move.reversal"]
            .with_context(active_ids=invoice.ids, active_model="account.move")
            .create({"reason": "prueba de signo", "journal_id": invoice.journal_id.id})
        )
        wizard.refund_moves()
        credit_note = invoice.reversal_move_ids
        with patch("arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar"):
            credit_note.action_post()

        # Instead of depending on a specific document type being in the core
        # list, this forces the code of this note into it: what is under test is
        # the sign behaviour, not the code table maintained by Odoo SA.
        code = credit_note.l10n_latam_document_type_id.code
        with patch.object(
            type(credit_note),
            "_get_l10n_ar_codes_used_for_inv_and_ref",
            return_value=[code],
        ):
            req = credit_note._l10n_ar_arca_build_fecae_request()

        det = req.FeDetReq.FECAEDetRequest[0]
        self.assertLess(det.ImpTotal, 0, "credit note with a reversible code")
        self.assertAlmostEqual(
            det.ImpTotal,
            det.ImpTotConc + det.ImpNeto + det.ImpOpEx + det.ImpTrib + det.ImpIVA,
            places=2,
            msg="identidade que a ARCA valida no cabecalho",
        )

    @_MUTE_EDI
    def test_communication_failure_is_reported_on_the_chatter(self):
        """The invoice stays posted without a CAE, but the user has to know it.

        Regression: `_post` only logged on the server. Whoever confirmed the
        invoice saw nothing, printed it and handed over a document with no CAE
        and no QR code.
        """
        invoice = self._create_factura_b()
        with patch(
            "arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar",
            side_effect=ConnectionError("ARCA fora do ar"),
        ):
            invoice.action_post()

        self.assertEqual(invoice.state, "posted")
        self.assertFalse(invoice.l10n_ar_arca_cae)
        bodies = " ".join(invoice.message_ids.mapped("body"))
        self.assertIn("ARCA fora do ar", bodies)
        self.assertIn("ARCA fora do ar", invoice.l10n_ar_arca_observations)

    @_MUTE_EDI
    def test_default_routing_is_wsfev1(self):
        invoice = self._create_factura_b()
        with patch("arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar"):
            invoice.action_post()
        self.assertEqual(invoice._l10n_ar_arca_webservice(), "wsfev1")

    @_MUTE_EDI
    def test_webservice_without_installed_module_raises_a_clear_error(self):
        """Routing to a webservice nobody implements.

        Happens when a module recognizes the document as belonging to another
        webservice (WSBFEv1, for instance) but the module serving it is not
        installed. An error naming the webservice beats an AttributeError about
        a missing method.
        """
        invoice = self._create_factura_b()
        with patch("arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar"):
            invoice.action_post()

        with (
            patch.object(
                type(invoice), "_l10n_ar_arca_webservice", return_value="wsbfev1"
            ),
            self.assertRaises(UserError) as ctx,
        ):
            invoice._l10n_ar_arca_request_cae()
        self.assertIn("wsbfev1", str(ctx.exception))

    @_MUTE_EDI
    def test_out_of_domain_response_does_not_break_the_posting(self):
        """Logging the failure must never be the reason the posting breaks.

        Regression: the logger wrote whatever ARCA had returned into
        `l10n_ar_arca_result`. A value outside the field domain (Selection A/R)
        made `write()` raise a ValueError OUTSIDE the try/except of `_post`,
        bringing down exactly the confirmation we wanted to preserve.
        """
        invoice = self._create_factura_b()
        fake_response = self._fake_fecae_response(resultado="A")
        # A value ARCA does not return today, but a future version of the
        # webservice (or a proxy in between) could.
        fake_response.FECAESolicitarResult.FeDetResp.FECAEDetResponse[0].Resultado = "X"

        with patch(
            "arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar",
            return_value=fake_response,
        ):
            invoice.action_post()

        self.assertEqual(invoice.state, "posted")
        self.assertFalse(invoice.l10n_ar_arca_cae)
        # Could not classify the result, but recorded what happened.
        self.assertFalse(invoice.l10n_ar_arca_result)
        self.assertTrue(invoice.l10n_ar_arca_observations)
