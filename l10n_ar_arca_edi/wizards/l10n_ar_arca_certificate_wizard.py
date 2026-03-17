# Copyright 2026 Leonobitech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo import fields, models, _
from odoo.exceptions import UserError


class L10nArArcaCertificateWizard(models.TransientModel):
    _name = "l10n_ar.arca.certificate.wizard"
    _description = "Upload ARCA Certificate Wizard"

    certificate_id = fields.Many2one(
        "l10n_ar.arca.certificate",
        string="Certificate",
        required=True,
    )
    certificate_file = fields.Binary(
        string="Certificate File (.crt)",
        required=True,
    )
    certificate_filename = fields.Char(string="Filename")

    def action_upload(self):
        """Process the uploaded certificate."""
        self.ensure_one()
        if not self.certificate_file:
            raise UserError(_("Please select a certificate file."))

        # Validate it's a valid PEM certificate
        cert_data = base64.b64decode(self.certificate_file)
        if b"-----BEGIN CERTIFICATE-----" not in cert_data:
            raise UserError(
                _(
                    "Invalid certificate format. Please upload the .crt file "
                    "downloaded from the ARCA portal."
                )
            )

        self.certificate_id.action_process_certificate(self.certificate_file)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Certificate Uploaded"),
                "message": _(
                    "Certificate has been activated successfully."
                ),
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window_close",
                },
            },
        }
