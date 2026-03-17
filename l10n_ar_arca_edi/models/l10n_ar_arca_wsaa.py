# Copyright 2026 Leonobitech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import datetime
import logging

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509 import load_pem_x509_certificate
from lxml import etree
from zeep import Client
from zeep.transports import Transport

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# WSAA endpoints
WSAA_URL = {
    "testing": "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl",
    "production": "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl",
}

# Argentina timezone offset
AR_TZ = datetime.timezone(datetime.timedelta(hours=-3))

# Token lifetime: request 12 hours
TOKEN_DURATION_HOURS = 12


class L10nArArcaWsaa(models.Model):
    _name = "l10n_ar.arca.wsaa"
    _description = "ARCA WSAA Authentication Service"

    @api.model
    def _get_or_refresh_token(self, certificate, service="wsfe"):
        """
        Get a valid WSAA token for the given service.
        If the cached token is still valid, return it.
        Otherwise, authenticate with ARCA and cache the new token.

        :param certificate: l10n_ar.arca.certificate record
        :param service: ARCA service name (e.g., 'wsfe', 'wsfex', 'wsbfe')
        :returns: dict with 'token' and 'sign' keys
        """
        certificate.ensure_one()

        if certificate.state != "active":
            raise UserError(
                _("Certificate '%s' is not active.", certificate.name)
            )

        # Check if cached token is still valid (with 10 min margin)
        now = fields.Datetime.now()
        if (
            certificate.wsaa_token
            and certificate.wsaa_sign
            and certificate.wsaa_token_expiration
            and certificate.wsaa_token_expiration
            > now + datetime.timedelta(minutes=10)
        ):
            return {
                "token": certificate.wsaa_token,
                "sign": certificate.wsaa_sign,
            }

        # Need to authenticate
        return self._authenticate(certificate, service)

    @api.model
    def _authenticate(self, certificate, service="wsfe"):
        """
        Perform WSAA LoginCMS authentication.

        Flow:
        1. Build a TRA (Ticket de Requerimiento de Acceso) XML
        2. Sign it with CMS/PKCS#7 using cryptography library
        3. Send the signed CMS to WSAA LoginCms endpoint
        4. Parse the response to extract Token and Sign

        :param certificate: l10n_ar.arca.certificate record
        :param service: ARCA service name
        :returns: dict with 'token' and 'sign' keys
        """
        certificate.ensure_one()

        # Step 1: Build TRA XML with Argentina timezone (-03:00)
        now = datetime.datetime.now(AR_TZ)
        generation_time = now - datetime.timedelta(minutes=10)
        expiration_time = now + datetime.timedelta(minutes=10)

        gen_str = generation_time.isoformat(timespec="seconds")
        exp_str = expiration_time.isoformat(timespec="seconds")

        tra_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<loginTicketRequest version="1.0">'
            "<header>"
            f"<uniqueId>{int(now.timestamp())}</uniqueId>"
            f"<generationTime>{gen_str}</generationTime>"
            f"<expirationTime>{exp_str}</expirationTime>"
            "</header>"
            f"<service>{service}</service>"
            "</loginTicketRequest>"
        )

        _logger.info(
            "WSAA: Authenticating for service '%s' (cert: %s, env: %s)",
            service,
            certificate.name,
            certificate.environment,
        )

        # Step 2: Sign TRA with CMS (PKCS#7) using cryptography library
        cms_signed = self._sign_tra(certificate, tra_xml)

        # Step 3: Call WSAA LoginCms
        wsdl_url = WSAA_URL[certificate.environment]
        try:
            transport = Transport(timeout=30, operation_timeout=30)
            client = Client(wsdl_url, transport=transport)
            response = client.service.loginCms(cms_signed)
        except Exception as e:
            _logger.error("WSAA LoginCms failed: %s", str(e))
            raise UserError(
                _("WSAA authentication failed: %s", str(e))
            ) from e

        # Step 4: Parse response
        token, sign, expiration = self._parse_login_response(response)

        # Cache token in certificate
        certificate.sudo().write({
            "wsaa_token": token,
            "wsaa_sign": sign,
            "wsaa_token_expiration": expiration,
        })

        _logger.info(
            "WSAA: Authentication successful. Token valid until %s",
            expiration,
        )

        return {"token": token, "sign": sign}

    @api.model
    def _sign_tra(self, certificate, tra_xml):
        """
        Sign the TRA XML using PKCS#7 (CMS) with the cryptography library.

        Uses PKCS7SignatureBuilder from the cryptography package, which is
        the clean, supported API (no pyOpenSSL internals needed).

        :param certificate: l10n_ar.arca.certificate record
        :param tra_xml: TRA XML string
        :returns: Base64-encoded CMS signature (DER format)
        """
        # Load private key
        key_pem = base64.b64decode(certificate.private_key)
        private_key = serialization.load_pem_private_key(
            key_pem, password=None
        )

        # Load certificate
        cert_pem = base64.b64decode(certificate.certificate)
        cert = load_pem_x509_certificate(cert_pem)

        # Sign using PKCS7SignatureBuilder
        signed = (
            pkcs7.PKCS7SignatureBuilder()
            .set_data(tra_xml.encode("utf-8"))
            .add_signer(cert, private_key, hashes.SHA256())
            .sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.Binary])
        )

        return base64.b64encode(signed).decode("utf-8")

    @api.model
    def _parse_login_response(self, response):
        """
        Parse the WSAA loginCms XML response.

        Expected format:
        <loginTicketResponse version="1.0">
            <header>
                <source>CN=wsaa, O=AFIP, C=AR</source>
                <destination>SERIALNUMBER=CUIT XX-XXXXXXXX-X, CN=...</destination>
                <uniqueId>...</uniqueId>
                <generationTime>2026-03-15T10:00:00-03:00</generationTime>
                <expirationTime>2026-03-15T22:00:00-03:00</expirationTime>
            </header>
            <credentials>
                <token>LARGO_STRING_DEL_TOKEN...</token>
                <sign>LARGO_STRING_DEL_SIGN...</sign>
            </credentials>
        </loginTicketResponse>

        :returns: tuple (token, sign, expiration_datetime)
        """
        try:
            root = etree.fromstring(response.encode("utf-8"))
        except etree.XMLSyntaxError as e:
            raise UserError(
                _("Failed to parse WSAA response: %s", str(e))
            ) from e

        token = root.findtext(".//token")
        sign = root.findtext(".//sign")
        expiration_str = root.findtext(".//expirationTime")

        if not token or not sign:
            raise UserError(
                _("WSAA response missing token or sign credentials.")
            )

        # Parse expiration time (ARCA returns -03:00 timezone)
        expiration = fields.Datetime.now() + datetime.timedelta(
            hours=TOKEN_DURATION_HOURS
        )
        if expiration_str:
            try:
                expiration = datetime.datetime.fromisoformat(expiration_str)
                # Convert to UTC naive datetime for Odoo storage
                expiration = expiration.astimezone(
                    datetime.timezone.utc
                ).replace(tzinfo=None)
            except (ValueError, TypeError):
                _logger.warning(
                    "Could not parse WSAA expiration time: %s",
                    expiration_str,
                )

        return token, sign, expiration
