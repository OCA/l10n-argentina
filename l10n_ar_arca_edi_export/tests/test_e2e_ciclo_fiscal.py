# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""End to end test of the Argentine sales fiscal cycle.

Unlike the per module tests (which exercise one method at a time), this one
walks the whole life cycle on a single coherent database, in the order a real
user follows: domestic invoice with VAT and a perception, credit note
referencing the original, and export invoice. At every step it checks the
payload **actually sent** to ARCA, not merely that the webservice was called.

Why this file exists: a review found the per module tests passing ("0 failed")
while the fiscal payload went out zeroed or incomplete, because none of them
inspected what was being sent. This test closes the cycle and is the one that
breaks if any module in the chain regresses on its own.

Runs against a mocked webservice (never touches the network). Validation against
the ARCA homologación environment is another layer, dependent on the customer
certificate.
"""

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_ar.tests.common import TestArCommon

_MUTE_EDI = mute_logger("odoo.addons.l10n_ar_arca_edi.models.account_move")


def _self_signed_cert_and_key_pem():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test.e2e")])
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


def _fake_fecae_response(cae="70111111111111"):
    """WSFEv1 approval response, built with the real arcalib bindings (not a
    MagicMock): if the binding changes shape, this test
    quebra, que é o comportamento desejado."""
    from arcalib.wsfev1.bindings.wsfev1 import (
        ArrayOfFecaedetResponse,
        FecaecabResponse,
        FecaedetResponse,
        Fecaeresponse,
        FecaesolicitarResponse,
    )

    det = FecaedetResponse(
        Concepto=1,
        DocTipo=80,
        DocNro=30714295698,
        CbteDesde=1,
        CbteHasta=1,
        Resultado="A",
        CAE=cae,
        CAEFchVto="20261231",
    )
    return FecaesolicitarResponse(
        FECAESolicitarResult=Fecaeresponse(
            FeCabResp=FecaecabResponse(
                Cuit=30111111118, PtoVta=3, CbteTipo=1, CantReg=1
            ),
            FeDetResp=ArrayOfFecaedetResponse(FECAEDetResponse=[det]),
        )
    )


def _fake_fex_response(cae="70222222222222"):
    """WSFEXv1 approval response, with the real bindings."""
    from arcalib.wsfexv1.bindings.wsfexv1 import (
        ClsFexoutAuthorize,
        FexauthorizeResponse,
        FexresponseAuthorize,
    )

    return FexauthorizeResponse(
        FEXAuthorizeResult=FexresponseAuthorize(
            FEXResultAuth=ClsFexoutAuthorize(
                Id=1,
                Cuit=30111111118,
                Cbte_tipo=19,
                Punto_vta=2,
                Cbte_nro=1,
                Resultado="A",
                Cae=cae,
                Fch_venc_Cae="20261231",
            )
        )
    )


@tagged("post_install", "-at_install")
class TestE2ECicloFiscal(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company_ri.l10n_ar_arca_environment = "homologacion"
        cert_pem, key_pem = _self_signed_cert_and_key_pem()
        cls.company_ri.l10n_ar_arca_certificate_id = cls.env[
            "certificate.certificate"
        ].create(
            {
                "name": "Certificado E2E",
                "company_id": cls.company_ri.id,
                "content": base64.b64encode(cert_pem + b"\n" + key_pem),
            }
        )
        cls.env.ref("base.es").l10n_ar_arca_cuit_pais = "203"
        cls.journal_interno = cls._create_journal(
            "wsfe",
            data={
                "l10n_ar_afip_pos_system": "RLI_RLM",
                "l10n_ar_afip_pos_number": "3",
            },
        )
        # Rate pinned only for the test: the core fixture comes with 0%,
        # because the real IIBB rate varies per jurisdiction.
        cls.tax_perc_iibb.amount = 3.0

    @_MUTE_EDI
    def test_full_cycle_invoice_credit_note_and_export(self):
        # --- step 1: domestic invoice, with 10.5 VAT and a perception ---
        invoice = self._create_invoice_ar(
            journal_id=self.journal_interno.id,
            partner_id=self.res_partner_adhoc.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_iva_105_perc,
                    price_unit=1000.0,
                    tax_ids=[Command.set([self.tax_10_5.id, self.tax_perc_iibb.id])],
                )
            ],
        )
        with patch(
            "arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar",
            return_value=_fake_fecae_response(),
        ) as wsfe:
            invoice.action_post()

        self.assertEqual(invoice.state, "posted")
        self.assertEqual(invoice.l10n_ar_arca_cae, "70111111111111")
        self.assertEqual(invoice.l10n_ar_arca_result, "A")

        det = wsfe.call_args.args[0].FeDetReq.FECAEDetRequest[0]
        # a identidade que a ARCA valida: o total tem que ser a soma exata
        # das parcelas informadas. E o que quebra quando os valores vao
        # zerados por chamar o helper do core sem base_lines.
        soma = det.ImpTotConc + det.ImpNeto + det.ImpOpEx + det.ImpTrib + det.ImpIVA
        self.assertAlmostEqual(soma, det.ImpTotal, places=2)
        self.assertAlmostEqual(det.ImpTotal, invoice.amount_total, places=2)
        self.assertAlmostEqual(det.ImpNeto, 1000.0, places=2)
        self.assertAlmostEqual(det.ImpIVA, 105.0, places=2)
        self.assertAlmostEqual(det.ImpTrib, 30.0, places=2)
        # The IIBB perception has to show up in the Tributos array, and the
        # sum of the array has to match ImpTrib (ARCA cross-checks the two).
        self.assertTrue(det.Tributos)
        self.assertAlmostEqual(
            sum(t.Importe for t in det.Tributos.Tributo), det.ImpTrib, places=2
        )
        # documento de identificacao do cliente: CUIT (80), numero sanitizado
        self.assertEqual(det.DocTipo, 80)
        self.assertEqual(det.DocNro, 30714295698)
        self.assertIsNone(det.CbtesAsoc)  # an invoice has no associated document

        # --- step 2: the legal QR of the document uses the CAE just stored ---
        qr = invoice._l10n_ar_arca_qr_data()
        self.assertEqual(qr["codAut"], 70111111111111)
        self.assertEqual(qr["importe"], invoice.amount_total)
        self.assertEqual(qr["cuit"], 30111111118)
        self.assertTrue(invoice._l10n_ar_arca_qr_url().startswith("https://"))

        # --- step 3: credit note referencing the original invoice ---
        wizard = (
            self.env["account.move.reversal"]
            .with_context(active_ids=invoice.ids, active_model="account.move")
            .create({"reason": "e2e", "journal_id": invoice.journal_id.id})
        )
        wizard.refund_moves()
        credit_note = invoice.reversal_move_ids
        with patch(
            "arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar",
            return_value=_fake_fecae_response(cae="70333333333333"),
        ) as wsfe_nc:
            credit_note.action_post()

        self.assertEqual(credit_note.l10n_ar_arca_cae, "70333333333333")
        det_nc = wsfe_nc.call_args.args[0].FeDetReq.FECAEDetRequest[0]
        # CbtesAsoc e o que torna a NC valida na ARCA: sem isso, rejeicao.
        self.assertTrue(det_nc.CbtesAsoc)
        asoc = det_nc.CbtesAsoc.CbteAsoc[0]
        self.assertEqual(asoc.Tipo, int(invoice.l10n_latam_document_type_id.code))
        self.assertEqual(asoc.PtoVta, self.journal_interno.l10n_ar_afip_pos_number)
        self.assertEqual(
            asoc.Nro,
            invoice._l10n_ar_get_document_number_parts(
                invoice.l10n_latam_document_number,
                invoice.l10n_latam_document_type_id.code,
            )["invoice_number"],
        )

        # --- step 4: export invoice goes to WSFEXv1, not WSFEv1 ---
        export_invoice = self._create_invoice_ar(
            journal_id=self.sale_expo_journal_ri.id,
            partner_id=self.res_partner_barcelona_food.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=500.0, product_id=self.product_iva_21
                )
            ],
        )
        export_invoice.l10n_ar_arca_tipo_expo = "1"
        self.assertTrue(export_invoice.l10n_ar_arca_is_export)

        with (
            patch(
                "arcalib.transmissao.wsfexv1.TransmissaoWSFEXv1.fex_authorize",
                return_value=_fake_fex_response(),
            ) as wsfex,
            patch(
                "arcalib.transmissao.wsfev1.TransmissaoWSFEv1.fecae_solicitar"
            ) as wsfe_nao_usado,
        ):
            export_invoice.action_post()

        # roteamento correto: exportacao NAO pode passar pelo WSFEv1
        wsfe_nao_usado.assert_not_called()
        wsfex.assert_called_once()
        self.assertEqual(export_invoice.l10n_ar_arca_cae, "70222222222222")

        cmp_export = wsfex.call_args.args[0]
        self.assertEqual(cmp_export.Cuit_pais_cliente, 203)
        self.assertTrue(cmp_export.Items)
        self.assertAlmostEqual(
            sum(item.Pro_total_item for item in cmp_export.Items.Item),
            export_invoice.amount_total,
            places=2,
        )

        # --- step 5: the three invoices coexist with their own distinct CAE ---
        caes = {
            invoice.l10n_ar_arca_cae,
            credit_note.l10n_ar_arca_cae,
            export_invoice.l10n_ar_arca_cae,
        }
        self.assertEqual(len(caes), 3)
