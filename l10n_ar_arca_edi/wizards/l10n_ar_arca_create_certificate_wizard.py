# Copyright 2026 Leonobitech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nArArcaCreateCertificateWizard(models.TransientModel):
    _name = "l10n_ar.arca.create.certificate.wizard"
    _description = "Create ARCA Certificate Wizard"

    name = fields.Char(
        string="Certificate Name",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    cuit = fields.Char(
        string="CUIT",
        compute="_compute_cuit",
        readonly=False,
    )
    environment = fields.Selection(
        [("testing", "Testing (Staging)"), ("production", "Production")],
        string="Environment",
        required=True,
        default="testing",
    )

    @api.depends("company_id")
    def _compute_cuit(self):
        for rec in self:
            vat = rec.company_id.partner_id.vat if rec.company_id else False
            if vat and len(vat.replace("-", "").replace(" ", "")) == 11:
                clean = vat.replace("-", "").replace(" ", "")
                rec.cuit = f"{clean[:2]}-{clean[2:10]}-{clean[10]}"
            else:
                rec.cuit = vat or ""

    def action_create(self):
        """Create the certificate and set it as active for the company."""
        self.ensure_one()
        cuit = self.company_id.partner_id.vat
        if not cuit:
            raise UserError(
                _("The selected company does not have a CUIT/VAT configured. "
                  "Set it in Settings > General Settings > Companies.")
            )

        cert = self.env["l10n_ar.arca.certificate"].create({
            "name": self.name,
            "company_id": self.company_id.id,
            "cuit": cuit,
            "environment": self.environment,
        })

        # Set as active certificate for the company
        self.company_id.l10n_ar_arca_certificate_id = cert

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Certificate Created"),
                "message": _("Certificate '%s' created. Now click 'Generate Key & CSR'.", cert.name),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }
