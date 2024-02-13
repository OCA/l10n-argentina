# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files


import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"  # pylint: disable=consider-merging-classes-inherited

    def _build_afip_wsfe_invoice(self, ws):
        ws.CrearFactura(**self._build_afip_wsfe_header())
        for vat_tax in self._build_afip_wsfe_vat_taxes():
            ws.AgregarIva(**vat_tax)
        for other_tax in self._build_afip_wsfe_other_taxes():
            ws.AgregarTributo(**other_tax)
        for cbte_asoc in self._build_afip_wsfe_cbte_asoc():
            ws.AgregarCmpAsoc(**cbte_asoc)
        for opt in self._build_afip_wsfe_opcionals():
            ws.AgregarOpcional(**opt)

    def _afip_ws_auth_wsfe(self, ws):
        ws.CAESolicitar()

    def _build_afip_wsfe_header(self):
        invoice = self._init_afip_base_header()
        # adapt date formats for WSFE
        invoice["fecha_cbte"] = invoice["fecha_cbte"].strftime("%Y%m%d")
        if invoice.get("fecha_venc_pago"):
            invoice["fecha_venc_pago"] = invoice["fecha_venc_pago"].strftime("%Y%m%d")
        if invoice.get("fecha_serv_desde"):
            invoice["fecha_serv_desde"] = invoice["fecha_serv_desde"].strftime("%Y%m%d")
        if invoice.get("fecha_serv_desde"):
            invoice["fecha_serv_hasta"] = invoice["fecha_serv_hasta"].strftime("%Y%m%d")
        return invoice

    def _build_afip_wsfe_vat_taxes(self):
        vat_taxes = self._get_vat()
        for tax in vat_taxes:
            tax["iva_id"] = tax.pop("Id")
            tax["base_imp"] = tax.pop("BaseImp")
            tax["importe"] = tax.pop("Importe")
        return vat_taxes

    def _build_afip_wsfe_other_taxes(self):
        other_taxes = []
        not_vat_taxes = self.line_ids.filtered(
            lambda x: x.tax_line_id
            and x.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code
        )
        for tax in not_vat_taxes:
            other_taxes.append(
                {
                    "tributo_id": tax.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code,
                    "ds": tax.tax_line_id.tax_group_id.name,
                    "base_imp": "%.2f"
                    % sum(
                        self.invoice_line_ids.filtered(
                            lambda x: x.tax_ids.filtered(
                                lambda y: y.tax_group_id.l10n_ar_tribute_afip_code
                                == tax.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code
                            )
                        ).mapped("price_subtotal")
                    ),
                    "alic": 0.00,
                    "importe": "%.2f" % abs(tax.amount_currency),
                }
            )
        return other_taxes

    def _build_afip_wsfe_cbte_asoc(self):
        cbte_asoc = []
        CbteAsoc = self.get_related_invoices_data()
        if CbteAsoc:
            doc_number_parts = self._l10n_ar_get_document_number_parts(
                CbteAsoc.l10n_latam_document_number,
                CbteAsoc.l10n_latam_document_type_id.code,
            )
            cbte_asoc.append(
                {
                    "tipo": CbteAsoc.l10n_latam_document_type_id.code,
                    "pto_vta": doc_number_parts["point_of_sale"],
                    "nro": doc_number_parts["invoice_number"],
                    "CUIT": self.company_id.vat,
                    "fecha": CbteAsoc.invoice_date.strftime("%Y%m%d"),
                }
            )
        return cbte_asoc

    def _build_afip_wsfe_opcionals(self):
        return []
