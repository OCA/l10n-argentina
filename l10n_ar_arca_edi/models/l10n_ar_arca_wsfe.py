# Copyright 2026 Leonobitech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from zeep import Client
from zeep.transports import Transport

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# WSFEv1 endpoints (Mercado Interno: Facturas A, B, C, M)
WSFE_URL = {
    "testing": "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL",
    "production": "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL",
}

# WSFEXv1 endpoints (Exportación: Facturas E)
WSFEX_URL = {
    "testing": "https://wswhomo.afip.gov.ar/wsfexv1/service.asmx?WSDL",
    "production": "https://servicios1.afip.gov.ar/wsfexv1/service.asmx?WSDL",
}

# WSBFEv1 endpoints (Bonos Fiscales Electrónicos)
WSBFE_URL = {
    "testing": "https://wswhomo.afip.gov.ar/wsbfev1/service.asmx?WSDL",
    "production": "https://servicios1.afip.gov.ar/wsbfev1/service.asmx?WSDL",
}

# WSCDC endpoints (Constatación de Comprobantes)
WSCDC_URL = {
    "testing": "https://wswhomo.afip.gov.ar/WSCDC/service.asmx?WSDL",
    "production": "https://servicios1.afip.gov.ar/WSCDC/service.asmx?WSDL",
}

# WS_SR_CONSTANCIA_INSCRIPCION endpoints (Consulta de Padrón)
WS_PADRON_URL = {
    "testing": "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5?WSDL",
    "production": "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5?WSDL",
}

# ARCA document type codes (código de comprobante)
ARCA_DOC_TYPES = {
    # Facturas
    1: "Factura A",
    6: "Factura B",
    11: "Factura C",
    19: "Factura E",
    51: "Factura M",
    # Notas de Débito
    2: "Nota de Débito A",
    7: "Nota de Débito B",
    12: "Nota de Débito C",
    20: "Nota de Débito E",
    # Notas de Crédito
    3: "Nota de Crédito A",
    8: "Nota de Crédito B",
    13: "Nota de Crédito C",
    21: "Nota de Crédito E",
    # Recibos
    4: "Recibo A",
    9: "Recibo B",
    15: "Recibo C",
    # Facturas de Crédito MiPyme
    201: "Factura de Crédito MiPyme A",
    206: "Factura de Crédito MiPyme B",
    211: "Factura de Crédito MiPyme C",
}

# ARCA concept types
ARCA_CONCEPT_TYPES = {
    1: "Productos",
    2: "Servicios",
    3: "Productos y Servicios",
}

# ARCA IVA aliquot codes
ARCA_IVA_CODES = {
    0: 3,       # 0% (Exento)
    2.5: 9,     # 2.5%
    5: 8,       # 5%
    10.5: 4,    # 10.5%
    21: 5,      # 21%
    27: 6,      # 27%
}

# ARCA document types for customer identification
ARCA_ID_DOC_TYPES = {
    "CUIT": 80,
    "CUIL": 86,
    "CDI": 87,
    "DNI": 96,
    "CI": 89,
    "LC": 90,
    "LE": 91,
    "passport": 94,
    "other": 99,
    "final_consumer": 99,
}

# WSAA service names for each web service
WSAA_SERVICE_NAMES = {
    "wsfe": "wsfe",
    "wsfex": "wsfex",
    "wsbfe": "wsbfe",
    "ws_sr_constancia_inscripcion": "ws_sr_constancia_inscripcion",
}


class L10nArArcaWsfe(models.Model):
    _name = "l10n_ar.arca.wsfe"
    _description = "ARCA WSFEv1 Electronic Invoice Service"

    @api.model
    def _get_client(self, certificate, service_urls=None):
        """Get a zeep SOAP client for the given service."""
        urls = service_urls or WSFE_URL
        wsdl_url = urls[certificate.environment]
        transport = Transport(timeout=30, operation_timeout=30)
        return Client(wsdl_url, transport=transport)

    @api.model
    def _get_auth(self, certificate, service="wsfe"):
        """Get the Auth dict required by all ARCA WS methods."""
        wsaa = self.env["l10n_ar.arca.wsaa"]
        credentials = wsaa._get_or_refresh_token(certificate, service=service)
        cuit = certificate.cuit.replace("-", "").replace(" ", "")
        return {
            "Token": credentials["token"],
            "Sign": credentials["sign"],
            "Cuit": int(cuit),
        }

    # -------------------------------------------------------------------------
    # WSFEv1 Methods (Mercado Interno)
    # -------------------------------------------------------------------------

    @api.model
    def fe_comp_ultimo_autorizado(self, certificate, pos_number, doc_type_code):
        """
        FECompUltimoAutorizado: Get the last authorized invoice number.

        :param certificate: l10n_ar.arca.certificate record
        :param pos_number: Point of sale number (int)
        :param doc_type_code: ARCA document type code (int)
        :returns: Last authorized invoice number (int)
        """
        client = self._get_client(certificate)
        auth = self._get_auth(certificate)

        try:
            response = client.service.FECompUltimoAutorizado(
                Auth=auth,
                PtoVta=pos_number,
                CbteTipo=doc_type_code,
            )
        except Exception as e:
            raise UserError(
                _("WSFE FECompUltimoAutorizado failed: %s", str(e))
            ) from e

        self._check_wsfe_errors(response)
        return response.CbteNro

    @api.model
    def fe_cae_solicitar(self, certificate, invoice_data):
        """
        FECAESolicitar: Request CAE for an invoice.

        :param certificate: l10n_ar.arca.certificate record
        :param invoice_data: dict with invoice details
        :returns: dict with 'cae', 'cae_due_date', 'result'
        """
        client = self._get_client(certificate)
        auth = self._get_auth(certificate)

        # Build FECAEDetRequest
        detail = {
            "Concepto": invoice_data["concept"],
            "DocTipo": invoice_data["customer_doc_type"],
            "DocNro": int(invoice_data["customer_doc_number"]),
            "CbteDesde": invoice_data["invoice_number"],
            "CbteHasta": invoice_data["invoice_number"],
            "CbteFch": invoice_data["date"],
            "ImpTotal": invoice_data["total"],
            "ImpTotConc": invoice_data["net_untaxed"],
            "ImpNeto": invoice_data["net_taxed"],
            "ImpOpEx": invoice_data["tax_exempt"],
            "ImpIVA": invoice_data["iva_total"],
            "ImpTrib": invoice_data.get("other_taxes", 0),
            "MonId": invoice_data.get("currency_code", "PES"),
            "MonCotiz": invoice_data.get("currency_rate", 1),
        }

        # Service dates (required for concept 2 and 3)
        if invoice_data["concept"] in (2, 3):
            detail["FchServDesde"] = invoice_data.get(
                "service_date_from", ""
            )
            detail["FchServHasta"] = invoice_data.get(
                "service_date_to", ""
            )
            detail["FchVtoPago"] = invoice_data.get("payment_due_date", "")

        # IVA lines
        if invoice_data.get("iva_lines"):
            detail["Iva"] = {
                "AlicIva": [
                    {
                        "Id": line["iva_id"],
                        "BaseImp": line["base"],
                        "Importe": line["amount"],
                    }
                    for line in invoice_data["iva_lines"]
                ]
            }

        # Associated documents (for credit/debit notes)
        if invoice_data.get("associated_docs"):
            detail["CbtesAsoc"] = {
                "CbteAsoc": [
                    {
                        "Tipo": doc["type"],
                        "PtoVta": doc["pos_number"],
                        "Nro": doc["number"],
                        "Cuit": doc.get("cuit", ""),
                        "CbteFch": doc.get("date", ""),
                    }
                    for doc in invoice_data["associated_docs"]
                ]
            }

        # Customer IVA condition (RG 5616 - mandatory since April 2025)
        if invoice_data.get("customer_iva_condition"):
            detail["CondicionIVAReceptorId"] = invoice_data[
                "customer_iva_condition"
            ]

        request_data = {
            "FeCabReq": {
                "CantReg": 1,
                "PtoVta": invoice_data["pos_number"],
                "CbteTipo": invoice_data["doc_type_code"],
            },
            "FeDetReq": {"FECAEDetRequest": [detail]},
        }

        _logger.info(
            "WSFE: Requesting CAE for PtoVta=%s CbteTipo=%s Nro=%08d",
            invoice_data["pos_number"],
            invoice_data["doc_type_code"],
            invoice_data["invoice_number"],
        )

        try:
            response = client.service.FECAESolicitar(
                Auth=auth, FeCAEReq=request_data
            )
        except Exception as e:
            raise UserError(
                _("WSFE FECAESolicitar failed: %s", str(e))
            ) from e

        self._check_wsfe_errors(response)
        result = self._parse_cae_response(response)

        _logger.info(
            "WSFE: CAE %s obtained (valid until %s). Result: %s",
            result.get("cae"),
            result.get("cae_due_date"),
            result.get("result"),
        )

        return result

    @api.model
    def fe_param_get_tipos_cbte(self, certificate):
        """FEParamGetTiposCbte: Get available document types."""
        client = self._get_client(certificate)
        auth = self._get_auth(certificate)
        try:
            response = client.service.FEParamGetTiposCbte(Auth=auth)
        except Exception as e:
            raise UserError(str(e)) from e
        self._check_wsfe_errors(response)
        return response.ResultGet.CbteTipo if response.ResultGet else []

    @api.model
    def fe_param_get_tipos_doc(self, certificate):
        """FEParamGetTiposDoc: Get available ID document types."""
        client = self._get_client(certificate)
        auth = self._get_auth(certificate)
        try:
            response = client.service.FEParamGetTiposDoc(Auth=auth)
        except Exception as e:
            raise UserError(str(e)) from e
        self._check_wsfe_errors(response)
        return response.ResultGet.DocTipo if response.ResultGet else []

    @api.model
    def fe_param_get_tipos_iva(self, certificate):
        """FEParamGetTiposIva: Get available IVA aliquot types."""
        client = self._get_client(certificate)
        auth = self._get_auth(certificate)
        try:
            response = client.service.FEParamGetTiposIva(Auth=auth)
        except Exception as e:
            raise UserError(str(e)) from e
        self._check_wsfe_errors(response)
        return response.ResultGet.IvaTipo if response.ResultGet else []

    @api.model
    def fe_param_get_ptos_venta(self, certificate):
        """FEParamGetPtosVenta: Get enabled points of sale."""
        client = self._get_client(certificate)
        auth = self._get_auth(certificate)
        try:
            response = client.service.FEParamGetPtosVenta(Auth=auth)
        except Exception as e:
            raise UserError(str(e)) from e
        self._check_wsfe_errors(response)
        return response.ResultGet.PtoVenta if response.ResultGet else []

    @api.model
    def fe_comp_consultar(
        self, certificate, pos_number, doc_type_code, invoice_number
    ):
        """FECompConsultar: Query an existing authorized invoice."""
        client = self._get_client(certificate)
        auth = self._get_auth(certificate)
        try:
            response = client.service.FECompConsultar(
                Auth=auth,
                FeCompConsReq={
                    "CbteTipo": doc_type_code,
                    "CbteNro": invoice_number,
                    "PtoVta": pos_number,
                },
            )
        except Exception as e:
            raise UserError(str(e)) from e
        self._check_wsfe_errors(response)
        return response.ResultGet

    # -------------------------------------------------------------------------
    # WSCDC Methods (Constatación de Comprobantes)
    # -------------------------------------------------------------------------

    @api.model
    def cdc_constatar_comprobante(
        self, certificate, doc_type, pos_number, invoice_number,
        date, total, cuit_emisor, doc_tipo_receptor, doc_nro_receptor,
    ):
        """
        ComprobanteConstatar: Verify an invoice's validity via WSCDC.

        :returns: dict with verification result
        """
        client = self._get_client(certificate, service_urls=WSCDC_URL)
        wsaa = self.env["l10n_ar.arca.wsaa"]
        credentials = wsaa._get_or_refresh_token(certificate, service="wsfe")
        cuit = certificate.cuit.replace("-", "").replace(" ", "")

        try:
            response = client.service.ComprobanteConstatar(
                Auth={
                    "Token": credentials["token"],
                    "Sign": credentials["sign"],
                    "Cuit": int(cuit),
                },
                CmpReq={
                    "CbteModo": "CAE",
                    "CuitEmisor": int(cuit_emisor),
                    "PtoVta": pos_number,
                    "CbteTipo": doc_type,
                    "CbteNro": invoice_number,
                    "CbteFch": date,
                    "ImpTotal": total,
                    "CodAutorizacion": "",
                    "DocTipoReceptor": doc_tipo_receptor,
                    "DocNroReceptor": int(doc_nro_receptor),
                },
            )
        except Exception as e:
            raise UserError(
                _("WSCDC verification failed: %s", str(e))
            ) from e

        return {
            "result": response.Resultado if hasattr(response, "Resultado") else None,
            "observations": str(response.Observaciones) if hasattr(response, "Observaciones") else "",
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @api.model
    def _parse_cae_response(self, response):
        """Parse FECAESolicitar response and extract CAE data."""
        result = {
            "cae": None,
            "cae_due_date": None,
            "result": None,
            "observations": [],
            "errors": [],
        }

        if not response or not response.FeDetResp:
            raise UserError(_("Empty response from WSFE."))

        det = response.FeDetResp.FECAEDetResponse[0]
        result["cae"] = det.CAE
        result["cae_due_date"] = det.CAEFchVto
        result["result"] = det.Resultado  # "A" = approved, "R" = rejected

        # Observations
        if det.Observaciones:
            for obs in det.Observaciones.Obs:
                result["observations"].append({
                    "code": obs.Code,
                    "message": obs.Msg,
                })

        # Global errors
        if response.Errors:
            for err in response.Errors.Err:
                result["errors"].append({
                    "code": err.Code,
                    "message": err.Msg,
                })

        if result["result"] == "R":
            error_msgs = [
                f"[{e['code']}] {e['message']}"
                for e in result["errors"] + result["observations"]
            ]
            raise UserError(
                _("ARCA rejected the invoice:\n%s", "\n".join(error_msgs))
            )

        return result

    @api.model
    def _check_wsfe_errors(self, response):
        """Check for global WSFE errors in the response."""
        if hasattr(response, "Errors") and response.Errors:
            errors = []
            for err in response.Errors.Err:
                errors.append(f"[{err.Code}] {err.Msg}")
            if errors:
                raise UserError(
                    _("WSFE Error:\n%s", "\n".join(errors))
                )
