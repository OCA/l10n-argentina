# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

import base64
import json
import logging
import sys
import traceback
from collections import defaultdict
from datetime import datetime

from pysimplesoap.client import SoapFault

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_repr

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    afip_document_number = fields.Char(
        copy=False, string="AFIP Document Number", readonly=True
    )
    afip_auth_mode = fields.Selection(
        [("CAE", "CAE"), ("CAI", "CAI"), ("CAEA", "CAEA")],
        string="AFIP authorization mode",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    afip_auth_code = fields.Char(
        copy=False,
        string="CAE/CAI/CAEA Code",
        readonly=True,
        oldname="afip_cae",
        size=24,
        states={"draft": [("readonly", False)]},
    )
    afip_auth_code_due = fields.Date(
        copy=False,
        readonly=True,
        oldname="afip_cae_due",
        string="CAE/CAI/CAEA due Date",
        states={"draft": [("readonly", False)]},
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
        states={"draft": [("readonly", False)]},
        copy=False,
        help="AFIP request result",
    )
    afip_qr_code = fields.Char(compute="_compute_qr_code", string="AFIP QR Code")

    @api.depends("l10n_latam_document_type_id")
    def _compute_name(self):
        """
        [MonkeyPatch] Fix sequence computation in batch:
        We need to group moves by document type since _compute_name will apply the
        same name prefix of the first record to the others in the batch
        TODO: PR a Odoo l10n_latam_invoice_document
        """
        without_doc_type = self.filtered(
            lambda x: x.journal_id.l10n_latam_use_documents
            and not x.l10n_latam_document_type_id
        )
        manual_documents = self.filtered(
            lambda x: x.journal_id.l10n_latam_use_documents
            and x.l10n_latam_manual_document_number
        )
        (
            without_doc_type
            + manual_documents.filtered(
                lambda x: not x.name
                or x.name
                and x.state == "draft"
                and not x.posted_before
            )
        ).name = "/"
        group_by_document_type = defaultdict(self.env["account.move"].browse)
        for move in self - without_doc_type - manual_documents:
            group_by_document_type[move.l10n_latam_document_type_id.id] += move
        for group in group_by_document_type.values():
            super(AccountMove, group)._compute_name()

    def _get_starting_sequence(self):
        """
        If use documents then will create a new starting sequence
        using the document type code prefix and the
        journal document number with a 8 padding number
        """
        if self.journal_id.l10n_latam_use_documents and self.journal_id.afip_ws:
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
        if (
            self._name == "account.move"
            and self.journal_id.l10n_latam_use_documents
            and self.journal_id.afip_ws
        ):
            last_sequence = self._get_last_sequence()
            new = not last_sequence
            if new:
                last_sequence = (
                    self._get_last_sequence(relaxed=True)
                    or self._get_starting_sequence()
                )
            iformat, format_values = self._get_sequence_format_param(last_sequence)
            if new:
                format_values["seq"] = int(
                    self.journal_id.get_pyafipws_last_invoice(
                        self.l10n_latam_document_type_id
                    )
                )
                format_values["year"] = self[self._sequence_date_field].year % (
                    10 ** format_values["year_length"]
                )
                format_values["month"] = self[self._sequence_date_field].month
            format_values["seq"] = format_values["seq"] + 1
            self[self._sequence_field] = iformat.format(**format_values)
            self._compute_split_sequence()
        else:
            super()._set_next_sequence()

    def _is_manual_document_number(self, journal):
        """
        If user is in debug_mode, we show the field as in manual input.
        This is useful for forcing AFIP webservice to retrieve an already authorized invoice
        in case sequence mismatches. Otherwise, it uses super normal functionality.
        """
        user_debug_mode = self.user_has_groups("base.group_no_one")
        return True if user_debug_mode else super()._is_manual_document_number(journal)

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
                    "ctz": float(float_repr(rec.l10n_ar_currency_rate, 2)),
                    "tipoCodAut": "E" if rec.afip_auth_mode == "CAE" else "A",
                    "codAut": int(rec.afip_auth_code),
                }
                if (
                    len(rec.commercial_partner_id.l10n_latam_identification_type_id)
                    and rec.commercial_partner_id.vat
                ):
                    qr_dict["tipoDocRec"] = int(
                        rec.commercial_partner_id.l10n_latam_identification_type_id.l10n_ar_afip_code  # noqa: B950
                    )
                    qr_dict["nroDocRec"] = int(
                        rec.commercial_partner_id.vat.replace("-", "").replace(".", "")
                    )
                qr_data = base64.encodestring(
                    json.dumps(qr_dict, indent=None).encode("ascii")
                ).decode("ascii")
                qr_data = str(qr_data).replace("\n", "")
                rec.afip_qr_code = "https://www.afip.gob.ar/fe/qr/?p=%s" % qr_data
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
        posted = super()._post(soft)
        posted_l10n_ar_invoices = self.filtered(
            lambda x: x.company_id.country_id.code == "AR"
            and x.is_invoice()
            and x.move_type in ["out_invoice", "out_refund"]
            and x.journal_id.afip_ws
            and not x.afip_auth_code
        ).sorted("id")
        posted_l10n_ar_invoices.authorize_afip()
        return posted

    def authorize_afip(self):
        for invoice in self:
            afip_ws = invoice.journal_id.afip_ws
            ws = invoice.company_id.get_connection(afip_ws).connect()
            invoice._build_afip_invoice(ws, afip_ws)
            invoice._get_ws_authorization(ws, afip_ws)
            invoice._parse_afip_response(ws, afip_ws)

    def _build_afip_invoice(self, ws, afip_ws):
        if not hasattr(self, "_build_afip_%s_invoice" % afip_ws):
            raise UserError(
                _(
                    "Autorizacion AFIP: ERROR. El webservice \
                    seleccionado %s no esta emplementado"
                )
                % afip_ws
            )
        return getattr(self, "_build_afip_%s_invoice" % afip_ws)(ws)

    def _get_ws_authorization(self, ws, afip_ws):
        error_msg = False
        try:
            if hasattr(self, "_afip_ws_auth_%s" % afip_ws):
                getattr(self, "_afip_ws_auth_%s" % afip_ws)(ws)
            else:
                raise UserError(
                    _("Error al autorizar comprobante. Webservice %s no implementado!")
                    % afip_ws
                )
        except SoapFault as soap_fault:
            error_msg = "Falla SOAP %s: %s" % (
                soap_fault.faultcode,
                soap_fault.faultstring,
            )
        except Exception as ex:
            error_msg = ex
        except Exception:
            if ws.Excepcion:
                error_msg = ws.Excepcion
            else:
                error_msg = traceback.format_exception_only(
                    sys.exc_type, sys.exc_value
                )[0]
        if error_msg:
            _logger.warning(
                _("AFIP Auth Error. %s" % error_msg)
                + " XML Request: %s XML Response: %s" % (ws.XmlRequest, ws.XmlResponse)
            )
            raise UserError(_("AFIP Validation Error. %s" % error_msg))

    def _parse_afip_response(self, ws, afip_ws):
        response_vals = {
            "afip_result": ws.Resultado,
            "afip_message": "\n".join([ws.Obs or "", ws.ErrMsg or ""]),
            "afip_xml_request": ws.XmlRequest,
            "afip_xml_response": ws.XmlResponse,
        }
        if ws.CAE and ws.Resultado == "A":
            response_vals["afip_auth_mode"] = "CAE"
            response_vals["afip_auth_code"] = ws.CAE
            cae_vto = afip_ws == "wsfex" and ws.FchVencCAE or ws.Vencimiento
            response_vals["afip_auth_code_due"] = datetime.strptime(
                cae_vto, "%Y%m%d"
            ).date()
            response_vals["afip_document_number"] = self._get_formatted_sequence(
                ws.CbteNro
            )
            _logger.info("CAE solicitado con exito.")
            _logger.info("CAE: %s. Resultado %s" % (ws.CAE, ws.Resultado))
        else:
            _logger.warning("AFIP Validation Error. Error en la obtencion del CAE.")
            _logger.warning(
                "AFIP Validation Error. Error: %s", response_vals["afip_message"]
            )
        self.write(response_vals)
        self._cr.commit()  # pylint: disable=invalid-commit

    def _init_afip_base_header(self):
        invoice = {}
        partner = self.commercial_partner_id
        amounts = self._l10n_ar_get_amounts()

        # Build basic header data
        invoice["concepto"] = invoice["tipo_expo"] = int(self.l10n_ar_afip_concept)
        invoice["tipo_doc"] = (
            partner.l10n_latam_identification_type_id.l10n_ar_afip_code or 99
        )
        invoice["nro_doc"] = self.l10n_latam_document_type_id.code and partner.vat or 0
        invoice["tipo_cbte"] = self.l10n_latam_document_type_id.code
        invoice["punto_vta"] = self.journal_id.l10n_ar_afip_pos_number
        invoice["fecha_cbte"] = self.invoice_date
        invoice["imp_total"] = str("%.2f" % self.amount_total)
        invoice["imp_tot_conc"] = str("%.2f" % amounts["vat_untaxed_base_amount"])
        invoice["imp_iva"] = str("%.2f" % amounts["vat_amount"])
        invoice["imp_trib"] = str("%.2f" % amounts["not_vat_taxes_amount"])
        invoice["imp_op_ex"] = str("%.2f" % amounts["vat_exempt_base_amount"])
        invoice["imp_neto"] = str("%.2f" % amounts["vat_taxable_amount"])
        invoice["moneda_id"] = self.currency_id.l10n_ar_afip_code
        invoice["moneda_ctz"] = self.l10n_ar_currency_rate

        # Caso de facturas "C"
        if self.l10n_latam_document_type_id.l10n_ar_letter == "C":
            invoice["imp_neto"] = str("%.2f" % self.amount_untaxed)

        # "fecha_serv_desde" y "fecha_serv_hasta" cuando el concepto es servicios
        if int(invoice["concepto"]) != 1:
            invoice["fecha_serv_desde"] = self.l10n_ar_afip_service_start
            invoice["fecha_serv_hasta"] = self.l10n_ar_afip_service_end

        # "fecha_venc_pago" solo en MiPyme FCE y Servicios
        if (
            invoice["concepto"] != 1
            and int(invoice["tipo_cbte"]) not in [202, 203, 207, 208, 212, 213]
            or int(invoice["tipo_cbte"]) in [201, 206, 211]
        ):
            invoice["fecha_venc_pago"] = self.invoice_date_due or self.invoice_date
            invoice["fecha_serv_desde"] = invoice["fecha_serv_hasta"] = None

        # asignacion del numero de comprobante desde AFIP
        cbte_nro = self._l10n_ar_get_document_number_parts(
            self.l10n_latam_document_number, self.l10n_latam_document_type_id.code
        )
        invoice["cbte_nro"] = cbte_nro["invoice_number"]
        invoice["cbt_desde"] = invoice["cbt_hasta"] = invoice["cbte_nro"]
        return invoice

    @api.constrains("invoice_incoterm_id", "journal_id")
    def _check_wsfex_incoterm(self):
        for record in self:
            if not record.invoice_incoterm_id and record.journal_id.afip_ws == "wsfex":
                raise ValidationError(
                    _("Facturas de exportacion (wsfex) deben tener incoterm asignado.")
                )
