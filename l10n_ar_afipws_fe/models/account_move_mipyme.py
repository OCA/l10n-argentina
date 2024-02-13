# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"  # pylint: disable=consider-merging-classes-inherited

    afip_fce_es_anulacion = fields.Boolean(
        string="FCE: Es anulacion?",
        help="Solo utilizado en comprobantes MiPyMEs (FCE) del tipo débito o crédito.\n"
        "- SI: sí el comprobante asociado se encuentra rechazado por el comprador\n"
        "- NO: sí el comprobante asociado NO se encuentra rechazado por el comprador",
    )

    def _build_afip_wsfe_opcionals(self):
        opcionales = super()._build_afip_wsfe_opcionals()
        doc_afip_code = self.l10n_latam_document_type_id.code
        mipyme_fce = int(doc_afip_code) in [201, 206, 211]
        if mipyme_fce:
            opcionales.append({"opcional_id": 2101, "valor": self.partner_bank_id.cbu})
            opcionales.append(
                {
                    "opcional_id": 27,
                    "valor": (
                        self.env["ir.config_parameter"]
                        .sudo()
                        .get_param("l10n_ar_afipws_fe.fce_transmission", "")
                    ),
                }
            )
        elif int(doc_afip_code) in [202, 203, 207, 208, 212, 213]:
            opcionales.append(
                {
                    "opcional_id": 22,
                    "valor": self.afip_fce_es_anulacion and "S" or "N",
                }
            )
        return opcionales
