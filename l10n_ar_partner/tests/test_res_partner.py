# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from odoo.tests.common import TransactionCase


def _self_signed_cert_and_key_pem():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test.l10n_ar_partner")])
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


class TestResPartnerUpdateFromPadron(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.country_id = cls.env.ref("base.ar")
        cls.company.l10n_ar_arca_environment = "homologacion"
        cls.company.partner_id.vat = "30-71234567-8"
        cert_pem, key_pem = _self_signed_cert_and_key_pem()
        cls.certificate = cls.env["certificate.certificate"].create(
            {
                "name": "Certificado de teste",
                "company_id": cls.company.id,
                "content": base64.b64encode(cert_pem + b"\n" + key_pem),
            }
        )
        cls.company.l10n_ar_arca_certificate_id = cls.certificate

        cuit_type = cls.env.ref("l10n_ar.it_cuit")
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Provisorio",
                "l10n_latam_identification_type_id": cuit_type.id,
                "vat": "20222222223",
            }
        )

    def _fake_get_persona(self, **kwargs):
        from arcalib.wspadron_a5.bindings.persona_service_a5 import (
            DatosGenerales,
            Domicilio,
            GetPersonaResponse,
            PersonaReturn,
        )

        return GetPersonaResponse(
            personaReturn=PersonaReturn(
                datosGenerales=DatosGenerales(
                    razonSocial="Empresa de Prueba SA",
                    tipoPersona="JURIDICA",
                    domicilioFiscal=Domicilio(
                        direccion="AV SIEMPRE VIVA 742",
                        localidad="BUENOS AIRES",
                        codPostal="1000",
                        descripcionProvincia="CIUDAD AUTONOMA BUENOS AIRES",
                    ),
                ),
                **kwargs,
            )
        )

    def test_updates_name_address_and_company_type(self):
        fake_response = self._fake_get_persona()
        with patch(
            "arcalib.transmissao.wspadron_a5.TransmissaoWSPadronA5.get_persona",
            return_value=fake_response,
        ) as mocked:
            self.partner.update_from_padron()

        # Regression: id_persona has to be the sanitized CUIT (int), not a raw
        # int(self.vat), which blows up on a formatted CUIT.
        mocked.assert_called_once_with(id_persona=20222222223)
        self.assertEqual(self.partner.name, "Empresa de Prueba SA")
        self.assertEqual(self.partner.company_type, "company")
        self.assertEqual(self.partner.street, "Av Siempre Viva 742")
        self.assertEqual(self.partner.city, "Buenos Aires")
        self.assertEqual(self.partner.zip, "1000")
        # Regression: the province returned by the padrón (uppercase,
        # unaccented, without "de") has to match the real name in
        # res.country.state ("Ciudad Autónoma de Buenos Aires").
        self.assertEqual(self.partner.state_id.name, "Ciudad Autónoma de Buenos Aires")

    def test_formatted_cuit_with_separators_does_not_raise(self):
        self.partner.vat = "20-22222222-3"
        fake_response = self._fake_get_persona()
        with patch(
            "arcalib.transmissao.wspadron_a5.TransmissaoWSPadronA5.get_persona",
            return_value=fake_response,
        ) as mocked:
            self.partner.update_from_padron()
        mocked.assert_called_once_with(id_persona=20222222223)

    def test_unmatched_province_leaves_state_id_unchanged(self):
        original_state = self.partner.state_id
        fake_response = self._fake_get_persona()
        domicilio = fake_response.personaReturn.datosGenerales.domicilioFiscal
        domicilio.descripcionProvincia = "PROVINCIA INEXISTENTE"
        with patch(
            "arcalib.transmissao.wspadron_a5.TransmissaoWSPadronA5.get_persona",
            return_value=fake_response,
        ):
            self.partner.update_from_padron()
        self.assertEqual(self.partner.state_id, original_state)

    def test_monotributo_sets_the_monotributo_responsibility(self):
        from arcalib.wspadron_a5.bindings.persona_service_a5 import DatosMonotributo

        fake_response = self._fake_get_persona(datosMonotributo=DatosMonotributo())
        with patch(
            "arcalib.transmissao.wspadron_a5.TransmissaoWSPadronA5.get_persona",
            return_value=fake_response,
        ):
            self.partner.update_from_padron()

        self.assertEqual(self.partner.l10n_ar_afip_responsibility_type_id.code, "6")

    def test_general_regime_with_active_vat_sets_responsable_inscripto(self):
        from arcalib.wspadron_a5.bindings.persona_service_a5 import (
            DatosRegimenGeneral,
            Impuesto,
        )

        fake_response = self._fake_get_persona(
            datosRegimenGeneral=DatosRegimenGeneral(
                impuesto=[
                    Impuesto(descripcionImpuesto="IVA", estadoImpuesto="AC"),
                ]
            )
        )
        with patch(
            "arcalib.transmissao.wspadron_a5.TransmissaoWSPadronA5.get_persona",
            return_value=fake_response,
        ):
            self.partner.update_from_padron()

        self.assertEqual(self.partner.l10n_ar_afip_responsibility_type_id.code, "1")

    def test_no_vat_signal_leaves_the_responsibility_unchanged(self):
        original = self.partner.l10n_ar_afip_responsibility_type_id
        fake_response = self._fake_get_persona()  # sem monotributo nem regimen geral
        with patch(
            "arcalib.transmissao.wspadron_a5.TransmissaoWSPadronA5.get_persona",
            return_value=fake_response,
        ):
            self.partner.update_from_padron()

        self.assertEqual(self.partner.l10n_ar_afip_responsibility_type_id, original)

    def test_without_cuit_marks_consumidor_final_without_calling_padron(self):
        dni_type = self.env.ref("l10n_ar.it_dni")
        partner_sem_cuit = self.env["res.partner"].create(
            {
                "name": "Pessoa Física",
                "l10n_latam_identification_type_id": dni_type.id,
                "vat": "22222222",
            }
        )
        with patch(
            "arcalib.transmissao.wspadron_a5.TransmissaoWSPadronA5.get_persona"
        ) as mocked:
            partner_sem_cuit.update_from_padron()
        mocked.assert_not_called()
        self.assertEqual(partner_sem_cuit.l10n_ar_afip_responsibility_type_id.code, "5")
