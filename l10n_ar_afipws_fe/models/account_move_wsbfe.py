# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files


import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"  # pylint: disable=consider-merging-classes-inherited

    def _build_afip_wsbfe_invoice(self, ws):
        ws.CrearFactura(**self._build_afip_wsbfe_header())
        for item in self._build_afip_wsbfe_items():
            ws.AgregarItem(**item)

    def _afip_ws_auth_wsbfe(self, ws):
        ws.Authorize(self.id)

    def _build_afip_wsbfe_header(self):
        invoice = self._init_afip_base_header()
        amounts = self._l10n_ar_get_amounts()
        # hardcoded zona=1 Nacional
        invoice["zona"] = 1
        # parse dates in WSBFE format
        invoice["fecha_cbte"] = invoice["fecha_cbte"].strftime("%Y%m%d")
        if invoice["fecha_venc_pago"]:
            invoice["fecha_venc_pago"] = invoice["fecha_venc_pago"].strftime("%Y%m%d")
        if invoice["fecha_serv_desde"]:
            invoice["fecha_serv_desde"] = invoice["fecha_serv_desde"].strftime("%Y%m%d")
        if invoice["fecha_serv_hasta"]:
            invoice["fecha_serv_hasta"] = invoice["fecha_serv_hasta"].strftime("%Y%m%d")
        # add wsbfe extra amounts
        invoice["impto_liq_rni"] = 0.0  # Ya no se usa
        invoice["imp_iibb"] = amounts["iibb_perc_amount"]
        invoice["imp_perc_mun"] = amounts["mun_perc_amount"]
        invoice["imp_internos"] = (
            amounts["intern_tax_amount"] + amounts["other_taxes_amount"]
        )
        invoice["imp_perc"] = (
            amounts["vat_perc_amount"]
            + amounts["profits_perc_amount"]
            + amounts["other_perc_amount"]
        )
        invoice["imp_moneda_id"] = invoice["moneda_id"]
        invoice["imp_moneda_ctz"] = invoice["moneda_ctz"]
        # TODO: asociated period in invoices with asociated document
        return invoice

    def _build_afip_wsbfe_items(self):
        items = []
        for line in self.invoice_line_ids:
            umed = line.product_uom_id and line.product_uom_id.l10n_ar_afip_code or "7"
            qty = line.quantity
            unitary_price = line.price_unit
            importe = line.price_subtotal
            bonif = (
                line.discount and str("%.2f" % (unitary_price * qty - importe)) or None
            )
            items.append(
                {
                    "codigo": line.product_id.default_code,
                    "sec": None,  # TODO:
                    "ds": line.name,
                    "qty": qty,
                    "umed": umed,
                    "precio": unitary_price,
                    "importe": importe,
                    "bonif": bonif,
                }
            )
        return items
