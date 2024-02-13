# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files


import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"  # pylint: disable=consider-merging-classes-inherited

    def _build_afip_wsfex_invoice(self, ws):
        ws.CrearFactura(**self._build_afip_wsfex_header())
        for item in self._build_afip_wsfex_items():
            ws.AgregarItem(**item)
        for cbte_asoc in self._build_afip_wsfex_cbte_asoc():
            ws.AgregarCmpAsoc(**cbte_asoc)
        for permiso in self._build_afip_wsfex_permisos():
            ws.AgregarPermiso(**permiso)

    def _afip_ws_auth_wsfex(self, ws):
        ws.Authorize(self.id)

    def _build_afip_wsfex_header(self):
        invoice = self._init_afip_base_header()
        country_id = self.commercial_partner_id.country_id
        partner = self.partner_id
        # adapt date formats for WSFEX
        invoice["fecha_cbte"] = invoice["fecha_cbte"].strftime("%Y%m%d")
        if invoice.get("fecha_venc_pago"):
            invoice["fecha_venc_pago"] = invoice["fecha_venc_pago"].strftime("%Y%m%d")
        if invoice.get("fecha_serv_desde"):
            invoice["fecha_serv_desde"] = invoice["fecha_serv_desde"].strftime("%Y%m%d")
        if invoice.get("fecha_serv_desde"):
            invoice["fecha_serv_hasta"] = invoice["fecha_serv_hasta"].strftime("%Y%m%d")
        # Validate country configuration
        if not country_id:
            raise UserError(
                _(
                    'For WS "%(afipws)s" country is required on partner'
                    % {"afipws": "self.journal_id.afip_ws"}
                )
            )
        elif not country_id.code:
            raise UserError(
                _(
                    'For WS "%(afipws)s" country code is mandatory'
                    'Country: "%(country)s"'
                    % {"afipws": self.journal_id.afip_ws, "country": country_id.name}
                )
            )
        elif not country_id.l10n_ar_afip_code:
            raise UserError(
                _(
                    'For WS "%(afipws)s" country code is mandatory'
                    'Country: "%(country)s"'
                    % {"afipws": self.journal_id.afip_ws, "country": country_id.name}
                )
            )
        # asignar campos extras header
        invoice["permiso_existente"] = "N"
        invoice["obs_generales"] = self.narration or None
        invoice["idioma_cbte"] = 1  # Español
        invoice["nombre_cliente"] = partner.name
        invoice["pais_dst_cmp"] = partner.country_id.l10n_ar_afip_code
        invoice["domicilio_cliente"] = " - ".join(
            [
                partner.name or "",
                partner.street or "",
                partner.street2 or "",
                partner.zip or "",
                partner.city or "",
            ]
        )
        # asignar incoterms
        if self.invoice_incoterm_id:
            invoice["incoterms"] = self.invoice_incoterm_id.code
            incoterms_ds = self.invoice_incoterm_id.name
            invoice["incoterms_ds"] = (
                incoterms_ds and incoterms_ds[:20]
            )  # Truncado a 20 caracteres
        else:
            invoice["incoterms"] = invoice["incoterms_ds"] = None
        # forma de pago y vencimiento
        if self.invoice_payment_term_id:
            invoice["forma_pago"] = self.invoice_payment_term_id.name
            invoice["obs_comerciales"] = self.invoice_payment_term_id.name
        else:
            invoice["forma_pago"] = invoice["obs_comerciales"] = None
        # fecha de pago
        if (
            int(invoice["tipo_cbte"]) == 19
            and invoice["tipo_expo"] in [2, 4]
            and self.invoice_date_due
        ):
            invoice["fecha_pago"] = self.invoice_date_due.strftime("%Y%m%d")
        # id_impositivo y cuit_pais
        if invoice["nro_doc"]:
            invoice["id_impositivo"] = invoice["nro_doc"]
            invoice["cuit_pais_cliente"] = None
        elif country_id.code != "AR" and invoice["nro_doc"]:
            invoice["id_impositivo"] = None
            if self.commercial_partner.is_company:
                invoice["cuit_pais_cliente"] = country_id.cuit_juridica
            else:
                invoice["cuit_pais_cliente"] = country_id.cuit_fisica
            if not invoice["cuit_pais_cliente"]:
                raise UserError(
                    _(
                        "No vat defined for the partner and also no CUIT "
                        "set on country"
                    )
                )
        # TODO: asociated period in invoices with asociated document
        return invoice

    def _build_afip_wsfex_cbte_asoc(self):
        return self._build_afip_wsfe_cbte_asoc()

    def _build_afip_wsfex_permisos(self):
        permisos = []
        return permisos

    def _build_afip_wsfex_items(self):
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
