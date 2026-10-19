# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

import logging

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AfipwsCertificateAlias(models.Model):
    _name = "afipws.certificate_alias"
    _description = "AFIP Distingish Name / Alias"
    _rec_name = "common_name"

    common_name = fields.Char(
        size=64,
        default="AFIP WS",
        help="Just a name, you can leave it this way",
        required=True,
    )
    key = fields.Text(
        "Private Key",
    )
    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.user.company_id,
        index=True,
    )
    country_id = fields.Many2one(
        "res.country",
        "Country",
        required=True,
    )
    state_id = fields.Many2one(
        "res.country.state",
        "State",
    )
    city = fields.Char(
        required=True,
    )
    department = fields.Char(
        default="IT",
        required=True,
    )
    cuit = fields.Char(
        "CUIT",
        compute="_compute_cuit",
        required=True,
    )
    company_cuit = fields.Char(
        "Company CUIT",
        size=16,
    )
    service_provider_cuit = fields.Char(
        "Service Provider CUIT",
        size=16,
    )
    certificate_ids = fields.One2many(
        "afipws.certificate",
        "alias_id",
        "Certificates",
    )
    service_type = fields.Selection(
        [("in_house", "En Casa"), ("outsourced", "Subcontratado")],
        default="in_house",
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("confirmed", "Confirmado"),
            ("cancel", "Cancelado"),
        ],
        "Status",
        index=True,
        readonly=True,
        default="draft",
        help="* The 'Draft' state is used when a user is creating a new pair "
        "key. Warning: everybody can see the key."
        "\n* The 'Confirmed' state is used when the key is completed with "
        "public or private key."
        "\n* The 'Canceled' state is used when the key is not more used. "
        "You cant use this key again.",
    )
    type = fields.Selection(
        [("production", "Producción"), ("homologation", "Homologación")],
        required=True,
        default="production",
    )

    @api.onchange("company_id")
    def change_company_name(self):
        if self.company_id:
            common_name = f"AFIP WS {self.type} - {self.company_id.name}"
            self.common_name = common_name[:50]

    @api.depends("company_cuit", "service_provider_cuit", "service_type")
    def _compute_cuit(self):
        for rec in self:
            if rec.service_type == "outsourced":
                rec.cuit = rec.service_provider_cuit
            else:
                rec.cuit = rec.company_cuit

    @api.onchange("company_id")
    def change_company_id(self):
        if self.company_id:
            self.country_id = self.company_id.country_id.id
            self.state_id = self.company_id.state_id.id
            self.city = self.company_id.city
            self.company_cuit = self.company_id.vat

    def action_confirm(self):
        if not self.key:
            self.generate_key()
        self.write({"state": "confirmed"})
        return True

    def generate_key(self, key_length=2048):
        """Generates a private key using cryptography library"""
        for rec in self:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_length,
            )
            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
            rec.key = pem.decode("ascii")

    def action_to_draft(self):
        self.write({"state": "draft"})
        return True

    def action_cancel(self):
        self.write({"state": "cancel"})
        self.certificate_ids.write({"state": "cancel"})
        return True

    def action_create_certificate_request(self):
        """Generates a certificate request to ask AFIP for the certificate"""
        for record in self:
            # Load the private key
            private_key = serialization.load_pem_private_key(
                record.key.encode("ascii"), password=None
            )

            # Build the subject name
            name_attributes = [
                x509.NameAttribute(
                    x509.NameOID.COUNTRY_NAME, record.country_id.code or "AR"
                ),
            ]
            if record.state_id and record.state_id.name:
                name_attributes.append(
                    x509.NameAttribute(
                        x509.NameOID.STATE_OR_PROVINCE_NAME, record.state_id.name
                    )
                )
            name_attributes.extend(
                [
                    x509.NameAttribute(x509.NameOID.LOCALITY_NAME, record.city or ""),
                    x509.NameAttribute(
                        x509.NameOID.ORGANIZATION_NAME, record.company_id.name or ""
                    ),
                    x509.NameAttribute(
                        x509.NameOID.ORGANIZATIONAL_UNIT_NAME, record.department or "IT"
                    ),
                    x509.NameAttribute(
                        x509.NameOID.COMMON_NAME, record.common_name or ""
                    ),
                    x509.NameAttribute(
                        x509.NameOID.SERIAL_NUMBER, "CUIT %s" % (record.cuit or "")
                    ),
                ]
            )

            # Create CSR
            csr = (
                x509.CertificateSigningRequestBuilder()
                .subject_name(x509.Name(name_attributes))
                .sign(private_key, hashes.SHA256())
            )

            csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode("ascii")

            vals = {
                "csr": csr_pem,
                "alias_id": record.id,
            }
            record.certificate_ids.create(vals)
        return True

    @api.constrains("common_name")
    def check_common_name_len(self):
        if self.filtered(lambda x: x.common_name and len(x.common_name) > 50):
            raise ValidationError(
                self.env._("The Common Name must be lower than 50 characters long")
            )
