# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

import logging
from base64 import encodebytes

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AfipwsCertificate(models.Model):
    _name = "afipws.certificate"
    _description = "afipws.certificate"
    _rec_name = "alias_id"

    alias_id = fields.Many2one(
        "afipws.certificate_alias",
        ondelete="cascade",
        string="Certificate Alias",
        required=True,
        index=True,
    )
    csr = fields.Text(
        "Request Certificate",
        help="Certificate Request in PEM format.",
    )
    crt = fields.Text(
        "Certificate",
        help="Certificate in PEM format.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("cancel", "Cancelled"),
        ],
        index=True,
        readonly=True,
        default="draft",
        help="* The 'Draft' state is used when a user is creating a new pair "
        "key. Warning: everybody can see the key."
        "\n* The 'Confirmed' state is used when a certificate is valid."
        "\n* The 'Canceled' state is used when the key is not more used. You "
        "cant use this key again.",
    )
    request_file = fields.Binary(
        "Download Signed Certificate Request",
        compute="_compute_request_file",
        readonly=True,
        store=True,
    )
    request_filename = fields.Char(
        "Filename", readonly=True, compute="_compute_request_file", store=True
    )
    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.user.company_id,
        index=True,
    )

    @api.depends("csr")
    def _compute_request_file(self):
        for rec in self.filtered("csr"):
            rec.request_filename = "request.csr"
            rec.request_file = encodebytes(rec.csr.encode("utf-8"))

    def action_to_draft(self):
        if self.alias_id.state != "confirmed":
            raise UserError(self.env._("Certificate Alias must be confirmed first!"))
        self.write({"state": "draft"})
        return True

    def action_cancel(self):
        self.write({"state": "cancel"})
        return True

    def action_confirm(self):
        self.verify_crt()
        self.write({"state": "confirmed"})
        return True

    def verify_crt(self):
        """
        Verify if certificate is well formed
        """
        for rec in self:
            crt = rec.crt
            msg = False

            if not crt:
                msg = self.env._(
                    "Invalid action! Please, set the certification string to continue."
                )
            certificate = rec.get_certificate()
            if certificate is None:
                msg = self.env._(
                    "Invalid action! Your certificate string is invalid. "
                    "Check if you forgot the header CERTIFICATE or forgot/ "
                    "append end of lines."
                )
            if msg:
                raise UserError(msg)
        return True

    def get_certificate(self):
        """
        Return Certificate object using cryptography library.
        """
        self.ensure_one()
        if self.crt:
            try:
                certificate = x509.load_pem_x509_certificate(self.crt.encode("ascii"))
            except Exception as e:
                err_msg = str(e)
                if "CERTIFICATE" in err_msg.upper():
                    raise UserError(
                        self.env._(
                            "Wrong Certificate file format.\nBe sure you have "
                            "BEGIN CERTIFICATE string in your first line."
                        )
                    ) from e
                else:
                    raise UserError(
                        self.env._(
                            "Unknown error.\nX509 return this message:\n %(error)s",
                            error=err_msg,
                        )
                    ) from e
        else:
            certificate = None
        return certificate

    def pkcs7_sign(self, message):
        """
        Sign message using PKCS7 with cryptography library.
        Similar to Enterprise l10n_ar_edi implementation.

        AFIP requires a PKCS7 signature with the certificate included
        and without additional capabilities/attributes.
        """
        self.ensure_one()

        if self.state != "confirmed":
            raise UserError(self.env._("Certificate must be confirmed before signing."))

        if not self.alias_id.key:
            raise UserError(self.env._("No private key linked to the certificate."))

        if not isinstance(message, bytes):
            message = message.encode("utf-8")

        try:
            cert = x509.load_pem_x509_certificate(self.crt.encode("ascii"))
            key = serialization.load_pem_private_key(
                self.alias_id.key.encode("ascii"), password=None
            )

            # AFIP requires specific PKCS7 options:
            # - Binary: treat data as binary (not text/canonical)
            # - NoAttributes: don't include authenticated attributes
            #   (superset of NoCapabilities)
            options = [
                pkcs7.PKCS7Options.Binary,
                pkcs7.PKCS7Options.NoAttributes,
            ]

            signature = (
                pkcs7.PKCS7SignatureBuilder()
                .set_data(message)
                .add_signer(cert, key, hashes.SHA256())
                .sign(serialization.Encoding.DER, options)
            )
            return signature
        except Exception as e:
            raise UserError(
                self.env._("Error signing message: %(error)s", error=str(e))
            ) from e

    def is_valid(self):
        """Check if certificate is valid (not expired)."""
        self.ensure_one()
        if not self.crt or self.state != "confirmed":
            return False
        try:
            cert = self.get_certificate()
            if cert:
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc)
                return cert.not_valid_before_utc <= now <= cert.not_valid_after_utc
        except Exception:
            return False
        return False
