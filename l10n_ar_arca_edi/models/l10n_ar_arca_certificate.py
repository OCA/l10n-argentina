# Copyright 2026 Leonobitech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509.oid import NameOID

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ARCA_ENVIRONMENTS = [
    ("testing", "Testing (Staging)"),
    ("production", "Production"),
]


class L10nArArcaCertificate(models.Model):
    _name = "l10n_ar.arca.certificate"
    _description = "ARCA Digital Certificate"
    _order = "id desc"

    name = fields.Char(
        string="Name",
        required=True,
        help="Symbolic name for this certificate (used as CN in the CSR)",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    cuit = fields.Char(
        string="CUIT",
        required=True,
        help="CUIT number (e.g., 20-29318820-4 or 20293188204)",
    )
    environment = fields.Selection(
        ARCA_ENVIRONMENTS,
        string="Environment",
        required=True,
        default="testing",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("csr_generated", "CSR Generated"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ],
        string="State",
        default="draft",
        readonly=True,
    )

    # Private key (stored encrypted in DB)
    private_key = fields.Binary(
        string="Private Key",
        attachment=True,
        groups="base.group_system",
        help="RSA 2048-bit private key in PEM format",
    )
    private_key_filename = fields.Char(string="Private Key Filename")

    # CSR
    csr = fields.Binary(
        string="Certificate Signing Request",
        attachment=True,
        readonly=True,
    )
    csr_filename = fields.Char(string="CSR Filename")
    csr_pem = fields.Text(
        string="CSR (PEM text)",
        readonly=True,
        help="CSR content in PEM format. Copy this to paste in ARCA portal.",
    )

    # Certificate (uploaded after ARCA signs the CSR)
    certificate = fields.Binary(
        string="Certificate",
        attachment=True,
    )
    certificate_filename = fields.Char(string="Certificate Filename")

    # Certificate info (populated after upload)
    cert_subject = fields.Char(string="Subject", readonly=True)
    cert_issuer = fields.Char(string="Issuer", readonly=True)
    cert_serial_number = fields.Char(string="Serial Number", readonly=True)
    cert_date_start = fields.Datetime(string="Valid From", readonly=True)
    cert_date_end = fields.Datetime(string="Valid Until", readonly=True)

    # WSAA token cache
    wsaa_token = fields.Text(string="WSAA Token", groups="base.group_system")
    wsaa_sign = fields.Text(string="WSAA Sign", groups="base.group_system")
    wsaa_token_expiration = fields.Datetime(
        string="Token Expiration",
        groups="base.group_system",
    )

    @api.constrains("cuit")
    def _check_cuit(self):
        for rec in self:
            cuit = rec.cuit.replace("-", "").replace(" ", "")
            if not cuit.isdigit() or len(cuit) != 11:
                raise UserError(
                    _("CUIT must be exactly 11 digits (e.g., 20-29318820-4).")
                )

    def _format_cuit_with_dashes(self):
        """Format CUIT as XX-XXXXXXXX-X for CSR serialNumber."""
        self.ensure_one()
        cuit = self.cuit.replace("-", "").replace(" ", "")
        return f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"

    def action_generate_key_and_csr(self):
        """Generate RSA 2048 private key and CSR for ARCA."""
        self.ensure_one()
        if self.state not in ("draft",):
            raise UserError(_("Can only generate CSR in draft state."))

        cuit_formatted = self._format_cuit_with_dashes()
        company_name = self.company_id.name or "Company"

        # Generate RSA 2048-bit private key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Serialize private key to PEM
        private_key_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Build CSR with ARCA-required fields
        # C=AR, O=company, CN=alias, serialNumber=CUIT XX-XXXXXXXX-X
        csr_builder = x509.CertificateSigningRequestBuilder().subject_name(
            x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "AR"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, company_name),
                x509.NameAttribute(NameOID.COMMON_NAME, self.name),
                x509.NameAttribute(
                    NameOID.SERIAL_NUMBER, f"CUIT {cuit_formatted}"
                ),
            ])
        )

        # Sign CSR with private key
        csr = csr_builder.sign(key, hashes.SHA256())

        # Serialize CSR to PEM
        csr_pem = csr.public_bytes(serialization.Encoding.PEM)

        self.write({
            "private_key": base64.b64encode(private_key_pem),
            "private_key_filename": f"{self.name}.key",
            "csr": base64.b64encode(csr_pem),
            "csr_filename": f"{self.name}.csr",
            "csr_pem": csr_pem.decode("utf-8"),
            "state": "csr_generated",
        })

        _logger.info(
            "Generated private key and CSR for certificate '%s' "
            "(CUIT: %s, env: %s)",
            self.name,
            cuit_formatted,
            self.environment,
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("CSR Generated"),
                "message": _(
                    "Private key and CSR have been generated. "
                    "Download the CSR and upload it to the ARCA portal "
                    "(%s environment).",
                    "WSASS Homologación"
                    if self.environment == "testing"
                    else "Administración de Certificados Digitales",
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_upload_certificate(self):
        """Open wizard to upload the signed certificate from ARCA."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Upload ARCA Certificate"),
            "res_model": "l10n_ar.arca.certificate.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_certificate_id": self.id},
        }

    def action_test_connection(self):
        """Test WSAA authentication with this certificate."""
        self.ensure_one()
        if self.state != "active":
            raise UserError(
                _("Certificate must be active to test the connection.")
            )

        wsaa = self.env["l10n_ar.arca.wsaa"]
        try:
            wsaa._get_or_refresh_token(self, service="wsfe")
        except UserError:
            raise
        except Exception as e:
            raise UserError(
                _("Connection test failed: %s", str(e))
            ) from e

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Connection Successful"),
                "message": _(
                    "WSAA authentication successful. Token valid until %s.",
                    self.wsaa_token_expiration.strftime("%Y-%m-%d %H:%M") if self.wsaa_token_expiration else "",
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_process_certificate(self, cert_data):
        """Process the uploaded certificate and extract metadata."""
        self.ensure_one()

        cert_pem = base64.b64decode(cert_data)
        cert = x509.load_pem_x509_certificate(cert_pem)

        self.write({
            "certificate": cert_data,
            "certificate_filename": f"{self.name}.crt",
            "cert_subject": cert.subject.rfc4514_string(),
            "cert_issuer": cert.issuer.rfc4514_string(),
            "cert_serial_number": str(cert.serial_number),
            "cert_date_start": cert.not_valid_before,
            "cert_date_end": cert.not_valid_after,
            "state": "active",
        })

        _logger.info(
            "Certificate '%s' activated. Valid until %s",
            self.name,
            cert.not_valid_after,
        )

    def action_revoke(self):
        """Mark certificate as revoked."""
        self.ensure_one()
        self.write({
            "state": "revoked",
            "wsaa_token": False,
            "wsaa_sign": False,
            "wsaa_token_expiration": False,
        })

    def _get_private_key(self):
        """Return the private key as a cryptography object."""
        self.ensure_one()
        if not self.private_key:
            raise UserError(
                _("No private key found for certificate '%s'.", self.name)
            )
        key_pem = base64.b64decode(self.private_key)
        return serialization.load_pem_private_key(key_pem, password=None)

    def _get_certificate(self):
        """Return the certificate as a cryptography x509 object."""
        self.ensure_one()
        if not self.certificate:
            raise UserError(
                _("No certificate found for '%s'. Upload the signed "
                  "certificate from ARCA first.", self.name)
            )
        cert_pem = base64.b64decode(self.certificate)
        return x509.load_pem_x509_certificate(cert_pem)

    def _cron_check_certificate_expiration(self):
        """Cron job to check certificate expiration and update state."""
        now = fields.Datetime.now()
        expired = self.search([
            ("state", "=", "active"),
            ("cert_date_end", "<", now),
        ])
        if expired:
            expired.write({"state": "expired"})
            _logger.warning(
                "Marked %d ARCA certificate(s) as expired: %s",
                len(expired),
                expired.mapped("name"),
            )
