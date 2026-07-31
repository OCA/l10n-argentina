# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ar_arca_verify_vendor_cae = fields.Char(
        string="Vendor CAE",
        copy=False,
        help="CAE printed on the document received from the vendor (entered by "
        "hand from the PDF or XML of the vendor bill). Used to check the "
        "document against ARCA (WSCDC).",
    )
    l10n_ar_arca_verify_result = fields.Char(
        string="Check result",
        copy=False,
        readonly=True,
        help="Text returned by ARCA in ComprobanteConstatarResult.Resultado. It "
        "is a Char and not a Selection: the possible values were not verified "
        "against the official specification (TO BE VERIFIED, see "
        "readme/ROADMAP.rst).",
    )
    l10n_ar_arca_verify_observations = fields.Text(
        string="Check remarks",
        copy=False,
        readonly=True,
        help="Remarks and errors returned by ARCA along with the result (why it "
        "was or was not validated).",
    )

    def action_l10n_ar_arca_verify_comprobante(self):
        """Check the vendor document against ARCA (WSCDC)."""
        for move in self:
            move._l10n_ar_arca_verify_comprobante()

    def _l10n_ar_arca_verify_comprobante(self):
        self.ensure_one()
        if self.move_type not in ("in_invoice", "in_refund"):
            raise UserError(_("Document checking only applies to vendor bills."))
        if not self.l10n_ar_arca_verify_vendor_cae:
            raise UserError(_("Enter the vendor CAE before checking."))

        transmissao = self.company_id._l10n_ar_arca_get_transmissao("TransmissaoWSCDC")
        cmp_datos = self._l10n_ar_arca_build_cmp_datos()
        response = transmissao.comprobante_constatar(cmp_datos)
        self._l10n_ar_arca_process_verify_response(response)

    def _l10n_ar_arca_build_cmp_datos(self):
        self.ensure_one()
        from arcalib.wscdc.bindings.wscdc import CmpDatos

        partner = self.partner_id
        # The receptor of the document is the company itself: it is the one
        # that received the vendor bill and is checking it.
        receptor = self.company_id.partner_id
        doc_number_parts = self._l10n_ar_get_document_number_parts(
            self.l10n_latam_document_number, self.l10n_latam_document_type_id.code
        )
        return CmpDatos(
            CbteModo="CAE",
            CuitEmisor=partner._get_id_number_sanitize(),
            PtoVta=doc_number_parts["point_of_sale"],
            CbteTipo=int(self.l10n_latam_document_type_id.code),
            CbteNro=doc_number_parts["invoice_number"],
            CbteFch=self.invoice_date.strftime("%Y%m%d") if self.invoice_date else None,
            ImpTotal=self.amount_total,
            CodAutorizacion=self.l10n_ar_arca_verify_vendor_cae,
            DocTipoReceptor=receptor.l10n_latam_identification_type_id.l10n_ar_afip_code
            or "99",
            DocNroReceptor=str(receptor._get_id_number_sanitize()),
        )

    def _l10n_ar_arca_process_verify_response(self, response):
        self.ensure_one()
        result = response.ComprobanteConstatarResult
        if not result:
            raise UserError(_("Unexpected response from ARCA: no result."))

        observations = []
        if result.Observaciones and result.Observaciones.Obs:
            observations.extend(
                f"[{obs.Code}] {obs.Msg}" for obs in result.Observaciones.Obs
            )
        if result.Errors and result.Errors.Err:
            observations.extend(f"[{err.Code}] {err.Msg}" for err in result.Errors.Err)

        self.write(
            {
                "l10n_ar_arca_verify_result": result.Resultado,
                "l10n_ar_arca_verify_observations": "; ".join(observations) or False,
            }
        )
