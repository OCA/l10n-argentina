# Copyright 2026 Leonobitech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Mapping from l10n_ar document type codes to ARCA CbteTipo codes
# l10n_ar uses the same codes as ARCA, so this is a validation set
SUPPORTED_ARCA_DOC_TYPES = {
    # Facturas
    1, 6, 11, 19, 51,
    # Notas de Débito
    2, 7, 12, 20,
    # Notas de Crédito
    3, 8, 13, 21,
    # Recibos
    4, 9, 15,
    # Facturas de Crédito MiPyme
    201, 206, 211,
}

# ARCA responsibility -> condition IVA receptor (RG 5616)
RESPONSIBILITY_TO_IVA_CONDITION = {
    1: 1,    # IVA Responsable Inscripto
    4: 4,    # IVA Sujeto Exento
    5: 5,    # Consumidor Final
    6: 6,    # Responsable Monotributo
    8: 8,    # Proveedor del Exterior
    9: 9,    # Cliente del Exterior
    10: 10,  # IVA Liberado
    11: 11,  # IVA Responsable Inscripto - Agente de Percepción
    13: 13,  # Monotributista Social
    15: 15,  # IVA No Alcanzado
}


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ar_arca_cae = fields.Char(
        string="CAE",
        readonly=True,
        copy=False,
        help="Código de Autorización Electrónico assigned by ARCA.",
    )
    l10n_ar_arca_cae_due_date = fields.Char(
        string="CAE Due Date",
        readonly=True,
        copy=False,
        help="CAE expiration date (YYYYMMDD format).",
    )
    l10n_ar_arca_result = fields.Selection(
        [
            ("A", "Approved"),
            ("R", "Rejected"),
            ("O", "Observed"),
        ],
        string="ARCA Result",
        readonly=True,
        copy=False,
    )
    l10n_ar_arca_observations = fields.Text(
        string="ARCA Observations",
        readonly=True,
        copy=False,
    )
    l10n_ar_arca_barcode = fields.Char(
        string="ARCA Barcode",
        readonly=True,
        copy=False,
        help="Barcode data for Interleaved 2 of 5 code on invoice PDF.",
    )
    l10n_ar_arca_qr_code = fields.Char(
        string="ARCA QR Code",
        readonly=True,
        copy=False,
        help="URL for ARCA QR code verification (RG 4892/2020).",
    )

    def action_verify_arca(self):
        """Verify this invoice's CAE against ARCA servers."""
        self.ensure_one()
        if not self.l10n_ar_arca_cae:
            raise UserError(_("This invoice has no CAE to verify."))

        certificate = self.company_id.l10n_ar_arca_certificate_id
        if not certificate:
            raise UserError(
                _("No active ARCA certificate configured for company '%s'.",
                  self.company_id.name)
            )

        doc_type_code = self._get_arca_doc_type_code()
        pos_number = self.journal_id.l10n_ar_afip_pos_number
        invoice_number = int(
            self.l10n_latam_document_number.split("-")[-1]
        )

        wsfe = self.env["l10n_ar.arca.wsfe"]
        try:
            result = wsfe.fe_comp_consultar(
                certificate, pos_number, doc_type_code, invoice_number
            )
        except UserError:
            raise
        except Exception as e:
            raise UserError(
                _("ARCA verification failed: %s", str(e))
            ) from e

        # Compare CAE from ARCA with local CAE
        # FECompConsultar returns CodAutorizacion, not CAE
        arca_cae = result.CodAutorizacion if hasattr(result, 'CodAutorizacion') else None
        arca_result = result.Resultado if hasattr(result, 'Resultado') else None
        arca_total = result.ImpTotal if hasattr(result, 'ImpTotal') else None
        raw_date = result.CbteFch if hasattr(result, 'CbteFch') else None
        arca_date = (
            f"{raw_date[6:8]}/{raw_date[4:6]}/{raw_date[0:4]}"
            if raw_date and len(str(raw_date)) == 8
            else raw_date
        )

        env_label = "Testing" if certificate.environment == "testing" else "Production"

        if arca_cae and str(arca_cae) == str(self.l10n_ar_arca_cae):
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("ARCA Verification - %s", env_label),
                    "message": _(
                        "CAE verified successfully.\n"
                        "CAE: %s\n"
                        "Result: %s\n"
                        "Total: %s\n"
                        "Date: %s",
                        arca_cae, arca_result, arca_total, arca_date,
                    ),
                    "type": "success",
                    "sticky": True,
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("ARCA Verification - %s", env_label),
                    "message": _(
                        "CAE mismatch!\n"
                        "Local CAE: %s\n"
                        "ARCA CAE: %s",
                        self.l10n_ar_arca_cae, arca_cae or "Not found",
                    ),
                    "type": "warning",
                    "sticky": True,
                },
            }

    def action_request_cae(self):
        """Manually request CAE from ARCA for this invoice."""
        self.ensure_one()
        if self.l10n_ar_arca_cae:
            raise UserError(
                _("This invoice already has a CAE: %s", self.l10n_ar_arca_cae)
            )
        self._l10n_ar_arca_request_cae()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("CAE Obtained"),
                "message": _(
                    "CAE: %s (valid until %s)",
                    self.l10n_ar_arca_cae,
                    self.l10n_ar_arca_cae_due_date,
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def _post(self, soft=True):
        """Override _post to automatically request CAE on invoice validation."""
        posted = super()._post(soft=soft)

        for move in posted:
            if (
                move.country_code == "AR"
                and move.is_invoice()
                and move.journal_id.l10n_ar_arca_edi_enabled
                and not move.l10n_ar_arca_cae
            ):
                try:
                    move._l10n_ar_arca_request_cae()
                except Exception as e:
                    _logger.error(
                        "Failed to get CAE for invoice %s: %s",
                        move.name,
                        str(e),
                    )
                    raise

        return posted

    def _l10n_ar_arca_request_cae(self):
        """Build invoice data and request CAE from ARCA."""
        self.ensure_one()

        certificate = self.company_id.l10n_ar_arca_certificate_id
        if not certificate:
            raise UserError(
                _(
                    "No active ARCA certificate configured for company '%s'. "
                    "Go to Settings > Invoicing > ARCA Electronic Invoicing.",
                    self.company_id.name,
                )
            )

        journal = self.journal_id
        if not journal.l10n_ar_arca_edi_enabled:
            raise UserError(
                _(
                    "ARCA electronic invoicing is not enabled for journal '%s'.",
                    journal.name,
                )
            )

        # Get document type code
        doc_type_code = self._get_arca_doc_type_code()

        # Get last authorized number
        wsfe = self.env["l10n_ar.arca.wsfe"]
        last_number = wsfe.fe_comp_ultimo_autorizado(
            certificate,
            journal.l10n_ar_afip_pos_number,
            doc_type_code,
        )
        next_number = last_number + 1

        # Build invoice data
        invoice_data = self._prepare_arca_invoice_data(
            certificate, journal, doc_type_code, next_number
        )

        # Request CAE
        result = wsfe.fe_cae_solicitar(certificate, invoice_data)

        # Build barcode data
        barcode = self._build_arca_barcode(
            certificate, doc_type_code, journal, result
        )

        # Build QR code URL (RG 4892/2020)
        qr_url = self._build_arca_qr_code(
            certificate, doc_type_code, journal, next_number, result
        )

        # Store results
        observations = ""
        if result.get("observations"):
            observations = "\n".join(
                f"[{o['code']}] {o['message']}"
                for o in result["observations"]
            )

        self.write({
            "l10n_ar_arca_cae": result["cae"],
            "l10n_ar_arca_cae_due_date": result["cae_due_date"],
            "l10n_ar_arca_result": result["result"],
            "l10n_ar_arca_observations": observations or False,
            "l10n_ar_arca_barcode": barcode,
            "l10n_ar_arca_qr_code": qr_url,
        })

    def _get_arca_doc_type_code(self):
        """Get the ARCA document type code for this invoice."""
        self.ensure_one()
        doc_type = self.l10n_latam_document_type_id
        if not doc_type:
            raise UserError(_("No document type set for this invoice."))
        code = int(doc_type.code)
        if code not in SUPPORTED_ARCA_DOC_TYPES:
            raise UserError(
                _(
                    "Document type '%s' (code %s) is not supported for "
                    "electronic invoicing.",
                    doc_type.name,
                    doc_type.code,
                )
            )
        return code

    def _prepare_arca_invoice_data(
        self, certificate, journal, doc_type_code, invoice_number
    ):
        """Prepare the data dict for FECAESolicitar."""
        self.ensure_one()

        partner = self.partner_id.commercial_partner_id

        # Determine concept type
        concept = self._get_arca_concept_type()

        # Customer document
        customer_doc_type, customer_doc_number = self._get_arca_customer_doc(
            partner
        )

        # Date
        invoice_date = self.invoice_date or fields.Date.today()
        date_str = invoice_date.strftime("%Y%m%d")

        # Amounts
        total = abs(self.amount_total)

        # Factura C (codes 11, 13, 15) does not discriminate IVA
        # All amount goes to ImpNeto, everything else is 0
        is_type_c = doc_type_code in (11, 13, 15)

        if is_type_c:
            net_taxed = total
            net_untaxed = 0
            tax_exempt = 0
            iva_total = 0
            iva_lines = []
        else:
            iva_total = 0
            net_taxed = 0
            tax_exempt = 0
            iva_lines = []

            for tax_line in self.line_ids.filtered(
                lambda l: l.tax_line_id
                and l.tax_line_id.tax_group_id.l10n_ar_vat_afip_code
            ):
                afip_code = int(
                    tax_line.tax_line_id.tax_group_id.l10n_ar_vat_afip_code
                )
                amount = abs(tax_line.balance)
                base = abs(tax_line.tax_base_amount)

                if afip_code == 3:  # Exento
                    tax_exempt += base
                else:
                    iva_total += amount
                    net_taxed += base
                    iva_lines.append({
                        "iva_id": afip_code,
                        "base": base,
                        "amount": amount,
                    })

            # Net untaxed (no gravado)
            net_untaxed = total - net_taxed - iva_total - tax_exempt

        data = {
            "pos_number": journal.l10n_ar_afip_pos_number,
            "doc_type_code": doc_type_code,
            "concept": concept,
            "customer_doc_type": customer_doc_type,
            "customer_doc_number": customer_doc_number,
            "invoice_number": invoice_number,
            "date": date_str,
            "total": total,
            "net_untaxed": max(net_untaxed, 0),
            "net_taxed": net_taxed,
            "tax_exempt": tax_exempt,
            "iva_total": iva_total,
            "iva_lines": iva_lines,
        }

        # Service dates
        if concept in (2, 3):
            data["service_date_from"] = date_str
            data["service_date_to"] = date_str
            due_date = self.invoice_date_due or invoice_date
            data["payment_due_date"] = due_date.strftime("%Y%m%d")

        # Associated documents (credit/debit notes)
        if self.move_type in ("out_refund", "in_refund"):
            origin = self.reversed_entry_id
            if origin:
                data["associated_docs"] = [
                    {
                        "type": int(
                            origin.l10n_latam_document_type_id.code
                        ),
                        "pos_number": journal.l10n_ar_afip_pos_number,
                        "number": int(
                            origin.l10n_latam_document_number.split("-")[-1]
                        ),
                        "cuit": certificate.cuit.replace("-", ""),
                        "date": origin.invoice_date.strftime("%Y%m%d"),
                    }
                ]

        # Customer IVA condition (RG 5616)
        if partner.l10n_ar_afip_responsibility_type_id:
            resp_code = int(
                partner.l10n_ar_afip_responsibility_type_id.code
            )
            if resp_code in RESPONSIBILITY_TO_IVA_CONDITION:
                data["customer_iva_condition"] = (
                    RESPONSIBILITY_TO_IVA_CONDITION[resp_code]
                )

        # Currency
        if self.currency_id != self.company_currency_id:
            data["currency_code"] = (
                self.currency_id.l10n_ar_afip_code or "PES"
            )
            data["currency_rate"] = self.currency_id.rate or 1

        return data

    def _get_arca_concept_type(self):
        """Determine ARCA concept type (1=products, 2=services, 3=both)."""
        self.ensure_one()
        has_product = any(
            line.product_id.type == "consu"
            for line in self.invoice_line_ids
            if line.product_id
        )
        has_service = any(
            line.product_id.type == "service"
            for line in self.invoice_line_ids
            if line.product_id
        )
        if has_product and has_service:
            return 3
        if has_service:
            return 2
        return 1

    def _get_arca_customer_doc(self, partner):
        """Get ARCA document type and number for the customer."""
        vat = partner.vat
        id_type = partner.l10n_latam_identification_type_id

        if not vat or not id_type:
            # Consumidor Final
            return 99, 0

        id_code = id_type.l10n_ar_afip_code
        if id_code:
            return int(id_code), int(
                vat.replace("-", "").replace(" ", "")
            )

        # Fallback
        return 99, 0

    def _build_arca_barcode(
        self, certificate, doc_type_code, journal, cae_result
    ):
        """
        Build the ARCA barcode data string for Interleaved 2 of 5.

        Format: CUIT + CbteTipo + PtoVta + CAE + CAEFchVto + DigitoVerificador

        The barcode encodes:
        - CUIT (11 digits)
        - Tipo de comprobante (3 digits, zero-padded)
        - Punto de venta (5 digits, zero-padded)
        - CAE (14 digits)
        - Fecha vencimiento CAE (8 digits, YYYYMMDD)
        - Dígito verificador (1 digit, mod 10)
        """
        if not cae_result.get("cae") or not cae_result.get("cae_due_date"):
            return False

        cuit = certificate.cuit.replace("-", "").replace(" ", "")
        cbte_tipo = str(doc_type_code).zfill(3)
        pto_vta = str(journal.l10n_ar_afip_pos_number).zfill(5)
        cae = str(cae_result["cae"]).zfill(14)
        cae_due = str(cae_result["cae_due_date"]).replace("-", "")

        # Build barcode without check digit
        barcode_data = f"{cuit}{cbte_tipo}{pto_vta}{cae}{cae_due}"

        # Calculate mod 10 check digit (Luhn-like for I2of5)
        odd_sum = sum(int(d) for d in barcode_data[::2])
        even_sum = sum(int(d) for d in barcode_data[1::2])
        total = odd_sum * 3 + even_sum
        check_digit = (10 - (total % 10)) % 10

        return f"{barcode_data}{check_digit}"

    def _build_arca_qr_code(
        self, certificate, doc_type_code, journal, invoice_number, cae_result
    ):
        """
        Build the ARCA QR code URL per RG 4892/2020.

        The QR encodes a JSON payload in base64:
        https://www.afip.gob.ar/fe/qr/?p={base64_json}
        """
        if not cae_result.get("cae") or not cae_result.get("cae_due_date"):
            return False

        cuit = certificate.cuit.replace("-", "").replace(" ", "")
        invoice_date = self.invoice_date or fields.Date.today()

        # Customer document
        partner = self.partner_id.commercial_partner_id
        customer_doc_type, customer_doc_number = self._get_arca_customer_doc(
            partner
        )

        # Currency code (PES = Argentine Peso)
        currency_code = "PES"
        currency_rate = 1
        if self.currency_id != self.company_currency_id:
            currency_code = (
                self.currency_id.l10n_ar_afip_code or "PES"
            )
            currency_rate = self.currency_id.rate or 1

        qr_data = {
            "ver": 1,
            "fecha": invoice_date.strftime("%Y-%m-%d"),
            "cuit": int(cuit),
            "ptoVta": journal.l10n_ar_afip_pos_number,
            "tipoCmp": doc_type_code,
            "nroCmp": invoice_number,
            "importe": round(abs(self.amount_total), 2),
            "moneda": currency_code,
            "ctz": currency_rate,
            "tipoDocRec": customer_doc_type,
            "nroDocRec": customer_doc_number,
            "tipoCodAut": "E",  # E = CAE
            "codAut": int(cae_result["cae"]),
        }

        json_str = json.dumps(qr_data, separators=(",", ":"))
        encoded = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")

        return f"https://www.afip.gob.ar/fe/qr/?p={encoded}"
