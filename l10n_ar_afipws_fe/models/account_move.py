# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

import base64
import json
import logging
from datetime import datetime

try:
    from zeep.exceptions import Fault as SoapFault
except ImportError:
    # Fallback if zeep is not available
    class SoapFault(Exception):
        def __init__(self, faultcode="", faultstring=""):
            self.faultcode = faultcode
            self.faultstring = faultstring
            super().__init__(faultstring)


from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_repr

from ..afip_tools import get_invoice_number_from_response

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    afip_auth_mode = fields.Selection(
        [("CAE", "CAE"), ("CAI", "CAI"), ("CAEA", "CAEA")],
        string="AFIP authorization mode",
        copy=False,
        readonly=True,
    )
    afip_auth_code = fields.Char(
        copy=False,
        string="CAE/CAI/CAEA Code",
        readonly=True,
        size=24,
    )
    afip_auth_code_due = fields.Date(
        copy=False,
        readonly=True,
        string="CAE/CAI/CAEA due Date",
    )
    afip_message = fields.Text(string="AFIP Message", copy=False, readonly=True)
    afip_xml_request = fields.Text(string="AFIP XML Request", copy=False, readonly=True)
    afip_xml_response = fields.Text(
        string="AFIP XML Response", copy=False, readonly=True
    )
    afip_result = fields.Selection(
        [("", "n/a"), ("A", "Aceptado"), ("R", "Rechazado"), ("O", "Observado")],
        "Resultado",
        readonly=True,
        copy=False,
        help="AFIP request result",
    )
    afip_qr_code = fields.Char(compute="_compute_qr_code", string="AFIP QR Code")
    asynchronous_post = fields.Boolean()

    def _get_l10n_ar_currency_rate(self):
        """
        Get the currency rate for AFIP.
        Returns 1.0 if currency is ARS, otherwise returns the exchange rate.
        """
        self.ensure_one()
        if self.currency_id == self.company_id.currency_id:
            return 1.0
        # Try to get the rate from the invoice date
        if self.currency_id and self.invoice_date:
            rate = self.currency_id._get_conversion_rate(
                self.currency_id,
                self.company_id.currency_id,
                self.company_id,
                self.invoice_date,
            )
            if rate:
                return round(1.0 / rate, 6) if rate != 0 else 1.0
        return 1.0

    @api.depends("journal_id", "l10n_latam_document_type_id")
    def _compute_highest_name(self):
        manual_records = self.filtered(
            lambda move: move.journal_id.afip_ws in ["wsfe", "wsfex", "wsbfe"]
        )
        manual_records.highest_name = ""
        return super(AccountMove, self - manual_records)._compute_highest_name()

    def _get_formatted_sequence(self, number=0):
        """
        Build the formatted invoice sequence for Argentina.
        Format: {doc_code_prefix} {point_of_sale:05d}-{invoice_number:08d}
        Example: FA-A 00003-00000115

        Args:
            number: Invoice number. Defaults to 0 for compatibility with
                    base l10n_ar module that calls this without arguments.
        """
        prefix = self.l10n_latam_document_type_id.doc_code_prefix
        pos = self.journal_id.l10n_ar_afip_pos_number
        return f"{prefix} {pos:05d}-{number:08d}"

    def _get_starting_sequence(self):
        """
        If use documents then will create a new starting
        sequence using the document type code prefix and the
        journal document number with a 8 padding number
        """
        if (
            self.journal_id.l10n_latam_use_documents
            and self.company_id.account_fiscal_country_id.code == "AR"
            and self.journal_id.afip_ws
        ):
            if self.l10n_latam_document_type_id:
                number = int(
                    self.journal_id.get_pyafipws_last_invoice(
                        self.l10n_latam_document_type_id
                    )
                )
                return self._get_formatted_sequence(number)
        return super()._get_starting_sequence()

    def _set_next_sequence(self):
        self.ensure_one()
        if self.afip_auth_code and self.journal_id.afip_ws and self.afip_xml_response:
            invoice_number = get_invoice_number_from_response(
                self.afip_xml_response, self.journal_id.afip_ws
            )
            if invoice_number:
                last_sequence = self._get_formatted_sequence(invoice_number)
                iformat, format_values = self._get_sequence_format_param(last_sequence)
                format_values["year"] = self[self._sequence_date_field].year % (
                    10 ** format_values["year_length"]
                )
                format_values["month"] = self[self._sequence_date_field].month
                format_values["seq"] = invoice_number
                self[self._sequence_field] = iformat.format(**format_values)
                return
        super()._set_next_sequence()

    @api.depends("afip_auth_code")
    def _compute_qr_code(self):
        for rec in self:
            if rec.afip_auth_mode in ["CAE", "CAEA"] and rec.afip_auth_code:
                number_parts = self._l10n_ar_get_document_number_parts(
                    rec.l10n_latam_document_number, rec.l10n_latam_document_type_id.code
                )

                qr_dict = {
                    "ver": 1,
                    "fecha": str(rec.invoice_date),
                    "cuit": int(rec.company_id.partner_id.l10n_ar_vat),
                    "ptoVta": number_parts["point_of_sale"],
                    "tipoCmp": int(rec.l10n_latam_document_type_id.code),
                    "nroCmp": number_parts["invoice_number"],
                    "importe": float(float_repr(rec.amount_total, 2)),
                    "moneda": rec.currency_id.l10n_ar_afip_code,
                    "ctz": float(float_repr(rec._get_l10n_ar_currency_rate(), 2)),
                    "tipoCodAut": "E" if rec.afip_auth_mode == "CAE" else "A",
                    "codAut": int(rec.afip_auth_code),
                }
                partner = rec.commercial_partner_id
                if len(partner.l10n_latam_identification_type_id) and partner.vat:
                    id_type = partner.l10n_latam_identification_type_id
                    qr_dict["tipoDocRec"] = int(id_type.l10n_ar_afip_code)
                    qr_dict["nroDocRec"] = int(
                        partner.vat.replace("-", "").replace(".", "")
                    )
                qr_data = base64.encodebytes(
                    json.dumps(qr_dict, indent=None).encode("ascii")
                ).decode("ascii")
                qr_data = str(qr_data).replace("\n", "")
                rec.afip_qr_code = f"https://www.afip.gob.ar/fe/qr/?p={qr_data}"
            else:
                rec.afip_qr_code = False

    def get_related_invoices_data(self):
        """
        List related invoice information to fill CbtesAsoc.
        """
        self.ensure_one()
        if self.l10n_latam_document_type_id.internal_type == "credit_note":
            return self.reversed_entry_id
        elif self.l10n_latam_document_type_id.internal_type == "debit_note":
            return self.debit_origin_id
        else:
            return self.browse()

    def _post(self, soft=True):
        posted_l10n_ar_invoices = self.filtered(
            lambda x: x.company_id.country_id.code == "AR"
            and x.is_invoice()
            and x.move_type in ["out_invoice", "out_refund"]
            and x.journal_id.afip_ws
            and not x.afip_auth_code
        )
        approved_invoices, rejected_invoices = posted_l10n_ar_invoices.authorize_afip()
        if len(self) == 1 and rejected_invoices:
            raise (UserError(rejected_invoices.afip_message))
        return super(AccountMove, self - rejected_invoices)._post(soft=soft)

    def authorize_afip(self):
        approved_invoices = rejected_invoices = self.env["account.move"]
        for invoice in self:
            afip_ws = invoice.journal_id.afip_ws
            ws = invoice.company_id.get_connection(afip_ws).connect()
            invoice._build_afip_invoice(ws, afip_ws)
            invoice._get_ws_authorization(ws, afip_ws)
            invoice._parse_afip_response(ws, afip_ws)
            if ws.Resultado == "A":
                approved_invoices += invoice
            else:
                rejected_invoices += invoice
        return approved_invoices, rejected_invoices

    def cron_asynchronous_post(self):
        queue_limit = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("l10n_ar_afipws_fe.queue_limit", 20)
        )
        queue = self.search(
            [
                ("asynchronous_post", "=", True),
                "|",
                ("afip_result", "=", False),
                ("afip_result", "=", "n/a"),
            ],
            limit=queue_limit,
        )
        if queue:
            queue._post()

    def _build_afip_invoice(self, ws, afip_ws):
        if not hasattr(self, f"_build_afip_{afip_ws}_invoice"):
            raise UserError(
                self.env._(
                    "Autorizacion AFIP: ERROR. El webservice "
                    "seleccionado %(ws)s no esta emplementado",
                    ws=afip_ws,
                )
            )
        return getattr(self, f"_build_afip_{afip_ws}_invoice")(ws)

    def _get_ws_authorization(self, ws, afip_ws):
        error_msg = False
        try:
            if hasattr(self, f"_afip_ws_auth_{afip_ws}"):
                getattr(self, f"_afip_ws_auth_{afip_ws}")(ws)
            else:
                raise UserError(
                    self.env._(
                        "Error al autorizar comprobante. "
                        "Webservice %(ws)s no implementado!",
                        ws=afip_ws,
                    )
                )
        except SoapFault as soap_fault:
            error_msg = f"Falla SOAP {soap_fault.faultcode}: {soap_fault.faultstring}"
        except Exception as ex:
            if ws.Excepcion:
                error_msg = ws.Excepcion
            else:
                error_msg = str(ex)
        if error_msg:
            formatted_message = (
                self.env._("AFIP Auth Error. %(error)s", error=error_msg)
                + f" XML Request: {ws.XmlRequest} XML Response: {ws.XmlResponse}"
            )
            _logger.error(formatted_message)
            self.write({"afip_message": formatted_message})

    def _parse_afip_response(self, ws, afip_ws):
        response_vals = {
            "afip_result": ws.Resultado,
            "afip_message": "\n".join([ws.Obs or "", ws.ErrMsg or ""]),
            "afip_xml_request": ws.XmlRequest,
            "afip_xml_response": ws.XmlResponse,
        }
        if ws.CAE and ws.Resultado == "A":
            cae_vto = (
                hasattr(ws, "FchVencCAE")
                and ws.FchVencCAE
                or hasattr(ws, "Vencimiento")
                and ws.Vencimiento
            )
            response_vals["afip_auth_mode"] = "CAE"
            response_vals["afip_auth_code"] = ws.CAE
            response_vals["afip_auth_code_due"] = datetime.strptime(
                cae_vto, "%Y%m%d"
            ).date()

            # Update invoice number from AFIP response
            invoice_number = get_invoice_number_from_response(ws.XmlResponse, afip_ws)
            if invoice_number:
                response_vals["name"] = self._get_formatted_sequence(invoice_number)
                _logger.info("Invoice number set to: %s", response_vals["name"])

            # Logging the result
            _logger.info("CAE solicitado con exito.")
            _logger.info(
                'Comprobante: "%s" CAE: "%s". Resultado "%s"',
                ws.CbteNro,
                ws.CAE,
                ws.Resultado,
            )

        else:
            response_vals["name"] = "/"
            # Logging the result
            _logger.warning("AFIP Validation Error. Error en la obtencion del CAE.")
            _logger.warning(
                "AFIP Validation Error. Error: %s", response_vals["afip_message"]
            )
            _logger.warning(
                "AFIP Validation Error. XML Request: %s",
                response_vals["afip_xml_request"],
            )
            _logger.warning(
                "AFIP Validation Error. XML Response: %s",
                response_vals["afip_xml_response"],
            )
        self.write(response_vals)
        self.env.cr.commit()  # pylint: disable=invalid-commit

    def _init_afip_base_header(self):
        invoice = {}
        partner = self.commercial_partner_id
        base_lines = self._get_rounded_base_and_tax_lines()[0]
        amounts = self._l10n_ar_get_amounts(base_lines)

        # ARCA expects positive amounts in credit and debit notes. Odoo's
        # localization returns negative components for refunds for reporting
        # purposes, while amount_total remains positive.
        if self.move_type in ("out_refund", "in_refund"):
            amounts = {key: abs(value) for key, value in amounts.items()}
            if not any(amounts.values()) and self.amount_total:
                vat_taxes = self._get_vat()
                amounts["vat_amount"] = sum(tax["Importe"] for tax in vat_taxes)
                amounts["vat_taxable_amount"] = sum(
                    tax["BaseImp"]
                    for tax in vat_taxes
                    if str(tax["Id"]) not in ("0", "1", "2")
                )
                amounts["vat_exempt_base_amount"] = sum(
                    tax["BaseImp"] for tax in vat_taxes if str(tax["Id"]) == "2"
                )
                amounts["vat_untaxed_base_amount"] = sum(
                    tax["BaseImp"] for tax in vat_taxes if str(tax["Id"]) == "1"
                )

        # Build basic header data
        invoice["concepto"] = invoice["tipo_expo"] = int(self.l10n_ar_afip_concept)
        invoice["tipo_doc"] = (
            partner.l10n_latam_identification_type_id.l10n_ar_afip_code or 99
        )
        invoice["nro_doc"] = self.l10n_latam_document_type_id.code and partner.vat or 0
        invoice["tipo_cbte"] = self.l10n_latam_document_type_id.code
        invoice["punto_vta"] = self.journal_id.l10n_ar_afip_pos_number
        invoice["fecha_cbte"] = self.invoice_date or fields.Date.today()
        invoice["imp_total"] = str(f"{self.amount_total:.2f}")
        invoice["imp_tot_conc"] = str(
            "{:.2f}".format(amounts["vat_untaxed_base_amount"])
        )
        invoice["imp_iva"] = str("{:.2f}".format(amounts["vat_amount"]))
        invoice["imp_trib"] = str("{:.2f}".format(amounts["not_vat_taxes_amount"]))
        invoice["imp_op_ex"] = str("{:.2f}".format(amounts["vat_exempt_base_amount"]))
        invoice["imp_neto"] = str("{:.2f}".format(amounts["vat_taxable_amount"]))
        invoice["moneda_id"] = self.currency_id.l10n_ar_afip_code
        invoice["moneda_ctz"] = self._get_l10n_ar_currency_rate()

        # Condición de IVA del receptor (obligatorio desde 01/02/2026 según RG 5616)
        if partner.l10n_ar_afip_responsibility_type_id:
            invoice["condicion_iva_receptor"] = int(
                partner.l10n_ar_afip_responsibility_type_id.code
            )

        # Caso de facturas "C"
        if self.l10n_latam_document_type_id.l10n_ar_letter == "C":
            invoice["imp_neto"] = str(f"{self.amount_untaxed:.2f}")

        # "fecha_serv_desde" y "fecha_serv_hasta" cuando concepto es servicios
        # Concepto 1=Productos, 2=Servicios, 3=Productos y Servicios
        # IMPORTANTE: Si se informa FchVtoPago, AFIP requiere fechas de servicio
        is_mipyme = int(invoice["tipo_cbte"]) in [201, 206, 211]
        needs_service_dates = int(invoice["concepto"]) != 1 or is_mipyme

        if needs_service_dates:
            # Fechas de servicio obligatorias si es servicio O si es MiPyme
            invoice_date = self.invoice_date or fields.Date.today()
            invoice["fecha_serv_desde"] = (
                self.l10n_ar_afip_service_start or invoice_date
            )
            invoice["fecha_serv_hasta"] = self.l10n_ar_afip_service_end or invoice_date
            # Fecha de vencimiento de pago: nunca puede ser anterior
            # a la fecha de comprobante
            due_date = self.invoice_date_due if self.invoice_date_due else invoice_date
            invoice["fecha_venc_pago"] = max(due_date, invoice_date)
        else:
            # Productos normales (no MiPyme): sin fechas
            invoice["fecha_serv_desde"] = None
            invoice["fecha_serv_hasta"] = None
            invoice["fecha_venc_pago"] = None

        # asignacion del numero de comprobante desde AFIP
        next_pyafipws_invoice_number = (
            int(
                self.journal_id.get_pyafipws_last_invoice(
                    self.l10n_latam_document_type_id
                )
            )
            + 1
        )
        invoice["cbte_nro"] = invoice["cbt_desde"] = invoice["cbt_hasta"] = (
            next_pyafipws_invoice_number
        )
        return invoice

    @api.constrains("invoice_incoterm_id", "journal_id")
    def _check_wsfex_incoterm(self):
        for record in self:
            if not record.invoice_incoterm_id and record.journal_id.afip_ws == "wsfex":
                raise ValidationError(
                    self.env._(
                        "Facturas de exportacion (wsfex) deben tener incoterm asignado."
                    )
                )

    def _get_vat(self):
        """Return the localized VAT breakdown with ARCA-positive amounts."""
        vat_taxes = super()._get_vat()
        for tax in vat_taxes:
            tax["BaseImp"] = abs(tax["BaseImp"])
            tax["Importe"] = abs(tax["Importe"])
        return vat_taxes
