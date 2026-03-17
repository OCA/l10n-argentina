# Copyright 2026 Leonobitech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Certificate selector (stored on company)
    l10n_ar_arca_certificate_id = fields.Many2one(
        related="company_id.l10n_ar_arca_certificate_id",
        readonly=False,
    )

    # --- Inline certificate setup fields ---

    # Company selector (dropdown from available companies)
    l10n_ar_arca_company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="company_id",
        readonly=False,
    )

    # Company CUIT (auto-filled from selected company)
    l10n_ar_arca_company_cuit = fields.Char(
        string="CUIT",
        compute="_compute_arca_company_cuit",
    )

    # Computed fields from selected certificate (readonly display)
    l10n_ar_arca_cert_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("csr_generated", "CSR Generated"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ],
        string="Connection Status",
        compute="_compute_arca_cert_fields",
    )
    l10n_ar_arca_cert_csr_pem = fields.Char(
        string="CSR Content",
        compute="_compute_arca_cert_fields",
    )
    l10n_ar_arca_cert_date_end = fields.Datetime(
        string="Valid Until",
        compute="_compute_arca_cert_fields",
    )
    l10n_ar_arca_cert_environment = fields.Char(
        string="Current Environment",
        compute="_compute_arca_cert_fields",
    )
    l10n_ar_arca_has_certificate = fields.Boolean(
        string="Has Certificate",
        compute="_compute_arca_cert_fields",
    )

    @api.depends("l10n_ar_arca_company_id")
    def _compute_arca_company_cuit(self):
        for rec in self:
            company = rec.l10n_ar_arca_company_id
            vat = company.partner_id.vat if company else False
            if vat and len(vat.replace("-", "").replace(" ", "")) == 11:
                clean = vat.replace("-", "").replace(" ", "")
                rec.l10n_ar_arca_company_cuit = (
                    f"{clean[:2]}-{clean[2:10]}-{clean[10]}"
                )
            else:
                rec.l10n_ar_arca_company_cuit = vat or ""

    @api.depends("l10n_ar_arca_certificate_id")
    def _compute_arca_cert_fields(self):
        for rec in self:
            cert = rec.l10n_ar_arca_certificate_id
            rec.l10n_ar_arca_has_certificate = bool(cert)
            rec.l10n_ar_arca_cert_state = cert.state if cert else False
            rec.l10n_ar_arca_cert_csr_pem = cert.csr_pem if cert else False
            rec.l10n_ar_arca_cert_date_end = cert.cert_date_end if cert else False
            rec.l10n_ar_arca_cert_environment = cert.environment if cert else False

    def action_arca_generate_csr(self):
        """Delegate CSR generation to the selected certificate."""
        self.ensure_one()
        cert = self.l10n_ar_arca_certificate_id
        if not cert:
            raise UserError(_("No certificate selected."))
        result = cert.action_generate_key_and_csr()
        # Reload settings to reflect new state
        if result and result.get("params"):
            result["params"]["next"] = {"type": "ir.actions.client", "tag": "reload"}
        return result

    def action_arca_upload_certificate(self):
        """Delegate certificate upload to the selected certificate."""
        self.ensure_one()
        cert = self.l10n_ar_arca_certificate_id
        if not cert:
            raise UserError(_("No certificate selected."))
        return cert.action_upload_certificate()

    def action_arca_test_connection(self):
        """Delegate connection test to the selected certificate."""
        self.ensure_one()
        cert = self.l10n_ar_arca_certificate_id
        if not cert:
            raise UserError(_("No certificate selected."))
        return cert.action_test_connection()
