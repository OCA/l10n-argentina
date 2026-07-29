# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

from odoo.addons.l10n_ar_arca_ws.models.res_company import AMBIENTE_ODOO_TO_ARCALIB


def _self_signed_cert_and_key_pem():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test.l10n_ar_arca_ws")])
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
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    return cert_pem, key_pem


class TestL10nArArcaWs(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.country_id = cls.env.ref("base.ar")
        cls.company.l10n_ar_arca_environment = "homologacion"

        cert_pem, key_pem = _self_signed_cert_and_key_pem()
        cls.certificate = cls.env["certificate.certificate"].create(
            {
                "name": "Certificado de prueba ARCA",
                "company_id": cls.company.id,
                "content": base64.b64encode(cert_pem + b"\n" + key_pem),
            }
        )
        cls.company.l10n_ar_arca_certificate_id = cls.certificate

    def test_certificate_has_a_linked_private_key(self):
        # Precondition for the rest of the tests: the PEM bundle (cert + key)
        # made the core detect and create the certificate.key automatically.
        self.assertTrue(self.certificate.private_key_id)
        self.assertTrue(self.certificate.is_valid)

    def test_missing_certificate_raises_usererror(self):
        self.company.l10n_ar_arca_certificate_id = False
        adapter = self.company._l10n_ar_arca_get_wsaa_adapter()
        with self.assertRaises(UserError):
            adapter.get_credentials("wsfev1")

    def test_certificate_without_private_key_raises_usererror(self):
        certificate_without_key = self.env["certificate.certificate"].create(
            {
                "name": "Certificado sin clave",
                "company_id": self.company.id,
                "content": base64.b64encode(
                    _self_signed_cert_and_key_pem()[0]  # only the cert, no key
                ),
            }
        )
        self.company.l10n_ar_arca_certificate_id = certificate_without_key
        adapter = self.company._l10n_ar_arca_get_wsaa_adapter()
        with self.assertRaises(UserError):
            adapter.get_credentials("wsfev1")

    def test_get_credentials_calls_arcalib_and_caches_in_db(self):
        expiration = datetime.now(timezone(timedelta(hours=-3))) + timedelta(hours=12)
        with patch(
            "arcalib.transmissao.wsaa.WSAA.get_credentials_with_expiration",
            return_value=("TOK-ODOO", "SIGN-ODOO", expiration),
        ) as mocked:
            adapter = self.company._l10n_ar_arca_get_wsaa_adapter()
            token, sign = adapter.get_credentials("wsfev1")

        self.assertEqual((token, sign), ("TOK-ODOO", "SIGN-ODOO"))
        mocked.assert_called_once()

        token_record = self.env["l10n_ar.arca.token"].search(
            [
                ("company_id", "=", self.company.id),
                ("servico", "=", "wsfev1"),
            ]
        )
        self.assertEqual(len(token_record), 1)
        self.assertEqual(token_record.token, "TOK-ODOO")
        # Regression: `expiration` arrives in UTC-3 (the arcalib offset); the
        # stored value (naive) must be the conversion to UTC, not the raw local
        # time (the previous bug expired the cache three hours early).
        expected_expiration_utc = expiration.astimezone(timezone.utc).replace(
            tzinfo=None
        )
        self.assertAlmostEqual(
            token_record.expiration,
            expected_expiration_utc,
            delta=timedelta(seconds=1),
        )

        # Second call hits the database cache, without calling arcalib again.
        with patch(
            "arcalib.transmissao.wsaa.WSAA.get_credentials_with_expiration"
        ) as mocked_second_call:
            adapter2 = self.company._l10n_ar_arca_get_wsaa_adapter()
            token2, sign2 = adapter2.get_credentials("wsfev1")

        mocked_second_call.assert_not_called()
        self.assertEqual((token2, sign2), ("TOK-ODOO", "SIGN-ODOO"))

    def test_expired_token_forces_renewal(self):
        past_expiration = datetime.now(timezone(timedelta(hours=-3))) - timedelta(
            hours=1
        )
        self.env["l10n_ar.arca.token"].create(
            {
                "company_id": self.company.id,
                "environment": "homologacion",
                "servico": "wscdc",
                "token": "TOK-OLD",
                "sign": "SIGN-OLD",
                "expiration": past_expiration.replace(tzinfo=None),
            }
        )
        new_expiration = datetime.now(timezone(timedelta(hours=-3))) + timedelta(
            hours=12
        )
        with patch(
            "arcalib.transmissao.wsaa.WSAA.get_credentials_with_expiration",
            return_value=("TOK-NEW", "SIGN-NEW", new_expiration),
        ) as mocked:
            adapter = self.company._l10n_ar_arca_get_wsaa_adapter()
            token, sign = adapter.get_credentials("wscdc")

        mocked.assert_called_once()
        self.assertEqual((token, sign), ("TOK-NEW", "SIGN-NEW"))

    def test_get_cuit_normalizes_a_formatted_vat(self):
        self.company.partner_id.vat = "30-71234567-8"
        self.assertEqual(self.company._l10n_ar_arca_get_cuit(), 30712345678)

    def test_get_cuit_without_vat_raises_usererror(self):
        self.company.partner_id.vat = False
        with self.assertRaises(UserError):
            self.company._l10n_ar_arca_get_cuit()

    def test_get_transmissao_builds_the_right_class_with_normalized_cuit(self):
        self.company.partner_id.vat = "30-71234567-8"
        from arcalib.transmissao import TransmissaoWSFEv1

        transmissao = self.company._l10n_ar_arca_get_transmissao("TransmissaoWSFEv1")
        self.assertIsInstance(transmissao, TransmissaoWSFEv1)
        self.assertEqual(transmissao.cuit, 30712345678)

    def test_get_transmissao_honours_the_alternative_cuit_kwarg(self):
        # TransmissaoWSPadronA5 names its parameter `cuit_representada`.
        self.company.partner_id.vat = "30-71234567-8"
        from arcalib.transmissao import TransmissaoWSPadronA5

        transmissao = self.company._l10n_ar_arca_get_transmissao(
            "TransmissaoWSPadronA5", cuit_kwarg="cuit_representada"
        )
        self.assertIsInstance(transmissao, TransmissaoWSPadronA5)

    def test_get_transmissao_environment_matches_the_selected_one(self):
        from arcalib.transmissao import HOMOLOGACION, PRODUCCION

        self.company.partner_id.vat = "30-71234567-8"
        self.company.l10n_ar_arca_environment = "homologacion"
        self.assertEqual(
            self.company._l10n_ar_arca_get_transmissao("TransmissaoWSFEv1").ambiente,
            HOMOLOGACION,
        )
        self.assertEqual(AMBIENTE_ODOO_TO_ARCALIB["produccion"], "PRODUCCION")
        self.company.l10n_ar_arca_environment = "produccion"
        self.assertEqual(
            self.company._l10n_ar_arca_get_transmissao("TransmissaoWSFEv1").ambiente,
            PRODUCCION,
        )

    def test_billing_user_gets_credentials_without_being_admin(self):
        """Whoever invoices is not an administrator, yet still needs a token.

        Regression: the adapter read and wrote `l10n_ar.arca.token` and read the
        `certificate.certificate` with the logged user env. Since the token ACL
        only grants write/create to `base.group_system` and the core certificate
        is only readable by an administrator, any billing user hit an
        AccessError and, in practice, only the admin could issue an invoice.
        """
        billing_user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Usuario de facturación",
                    "login": "billing.arca@example.org",
                    "company_id": self.company.id,
                    "company_ids": [(6, 0, self.company.ids)],
                    "groups_id": [
                        (4, self.env.ref("account.group_account_invoice").id),
                    ],
                }
            )
        )
        self.assertFalse(billing_user.has_group("base.group_system"))

        adapter = (
            self.env["l10n_ar.arca.token"]
            .with_user(billing_user)
            ._get_wsaa_adapter(self.company.with_user(billing_user))
        )
        expiration = datetime.now(timezone.utc) + timedelta(hours=12)
        with patch(
            "arcalib.transmissao.wsaa.WSAA.get_credentials_with_expiration",
            return_value=("TOK-USER", "SIGN-USER", expiration),
        ):
            token, sign = adapter.get_credentials("wsfev1")

        self.assertEqual((token, sign), ("TOK-USER", "SIGN-USER"))
        # Cached even though the user has no write access to the model.
        cached = self.env["l10n_ar.arca.token"].search(
            [("company_id", "=", self.company.id), ("servico", "=", "wsfev1")]
        )
        self.assertEqual(len(cached), 1)
