# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    afip_fce_es_anulacion = fields.Boolean(
        string="FCE: Es anulacion?",
        help="""
        Solo utilizado en comprobantes MiPyMEs (FCE)
        del tipo débito o crédito. Debe informar:\n
        "- SI: sí el comprobante asociado (original) se
        encuentra rechazado por el comprador\n"
        "- NO: sí el comprobante asociado (original) NO se
        encuentra rechazado por el comprador
        """,
    )
    afip_mypyme_sca_adc = fields.Selection(
        selection=[
            ("SCA", "SCA - Sistema Circulacion Abierta"),
            ("ADC", "AGC - Agente Deposito Colectivo"),
        ],
        string="FCE: Opcion de Trasmision",
        default="SCA",
    )

    def _build_afip_wsfe_opcionals(self):
        opcionales = super()._build_afip_wsfe_opcionals()
        doc_afip_code = self.l10n_latam_document_type_id.code
        mipyme_fce = int(doc_afip_code) in [201, 206, 211]
        if mipyme_fce:
            # agregamos cbu para factura de credito electronica
            opcionales.append({"opcional_id": 2101, "valor": self.partner_bank_id.cbu})
            opcionales.append({"opcional_id": 27, "valor": self.afip_mypyme_sca_adc})
        elif int(doc_afip_code) in [202, 203, 207, 208, 212, 213]:
            opcionales.append(
                {
                    "opcional_id": 22,
                    "valor": self.afip_fce_es_anulacion and "S" or "N",
                }
            )
        return opcionales
