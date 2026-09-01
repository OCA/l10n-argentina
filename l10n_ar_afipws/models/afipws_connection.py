# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

import logging

from lxml import etree

from odoo import api, fields, models
from odoo.exceptions import UserError

try:
    from requests import Session
    from requests.adapters import HTTPAdapter
    from urllib3.util.ssl_ import create_urllib3_context
    from zeep import Client, Transport
    from zeep.helpers import serialize_object
except ImportError:
    try:
        from requests import Session
        from requests.adapters import HTTPAdapter
        from urllib3.util.ssl_ import create_urllib3_context

        from odoo.tools.zeep import Client, Transport
        from odoo.tools.zeep.helpers import serialize_object
    except ImportError:
        Client = None
        Transport = None
        serialize_object = None
        Session = None
        HTTPAdapter = None
        create_urllib3_context = None

_logger = logging.getLogger(__name__)


class AFIPHTTPAdapter(HTTPAdapter):
    """Custom HTTP adapter that allows weak DH keys used by AFIP servers."""

    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def _get_afip_session():
    """Create a requests session configured for AFIP servers."""
    session = Session()
    session.verify = True
    session.mount("https://", AFIPHTTPAdapter())
    return session


class AfipwsConnection(models.Model):
    _name = "afipws.connection"
    _description = "AFIP WS Connection"
    _rec_name = "afip_ws"
    _order = "expirationtime desc"

    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        index=True,
    )
    uniqueid = fields.Char(
        "Unique ID",
        readonly=True,
    )
    token = fields.Text(
        readonly=True,
    )
    sign = fields.Text(
        readonly=True,
    )
    generationtime = fields.Datetime("Generation Time", readonly=True)
    expirationtime = fields.Datetime("Expiration Time", readonly=True)
    afip_login_url = fields.Char(
        "AFIP Login URL",
        compute="_compute_afip_urls",
    )
    afip_ws_url = fields.Char(
        "AFIP WS URL",
        compute="_compute_afip_urls",
    )
    type = fields.Selection(
        [("production", "Producción"), ("homologation", "Homologación")],
        required=True,
    )
    afip_ws = fields.Selection(
        [
            ("ws_sr_padron_a4", "Servicio de Consulta de Padrón Alcance 4"),
            ("ws_sr_padron_a5", "Servicio de Consulta de Padrón Alcance 5"),
            ("ws_sr_padron_a10", "Servicio de Consulta de Padrón Alcance 10"),
            ("ws_sr_padron_a100", "Servicio de Consulta de Padrón Alcance 100"),
        ],
        "AFIP WS",
        required=True,
    )

    # Store XML request/response for debugging
    xml_request = fields.Text("XML Request", readonly=True)
    xml_response = fields.Text("XML Response", readonly=True)

    @api.depends("type", "afip_ws")
    def _compute_afip_urls(self):
        for rec in self:
            rec.afip_login_url = rec.get_afip_login_url(rec.type)
            afip_ws_url = rec.get_afip_ws_url(rec.afip_ws, rec.type)
            rec.afip_ws_url = afip_ws_url or ""

    @api.model
    def get_afip_login_url(self, environment_type):
        if environment_type == "production":
            afip_login_url = "https://wsaa.afip.gov.ar/ws/services/LoginCms"
        else:
            afip_login_url = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"
        return afip_login_url

    @api.model
    def get_afip_ws_url(self, afip_ws, environment_type):
        """
        Function to be inherited on each module that adds a new webservice.
        Returns the WSDL URL for the given webservice and environment.
        """
        _logger.info("Getting URL for afip ws %s on %s", afip_ws, environment_type)

        ws_urls = {
            "ws_sr_padron_a4": {
                "production": "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA4?wsdl",
                "homologation": "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA4?wsdl",
            },
            "ws_sr_padron_a5": {
                "production": "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5?wsdl",
                "homologation": "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5?wsdl",
            },
        }

        return ws_urls.get(afip_ws, {}).get(environment_type, False)

    def _get_client(self, return_transport=False):
        """Get zeep client to connect to the webservice.

        Returns (client, auth_dict) or (client, auth_dict, transport)
        if return_transport=True.
        """
        self.ensure_one()
        wsdl = self.afip_ws_url
        if not wsdl:
            raise UserError(
                self.env._(
                    "AFIP Webservice %(ws)s not supported or URL not configured",
                    ws=self.afip_ws,
                )
            )

        auth = {
            "Token": self.token,
            "Sign": self.sign,
            "Cuit": self.company_id.vat,
        }

        try:
            # Use custom session with SSL adapter for AFIP compatibility
            session = _get_afip_session()
            transport = Transport(session=session, operation_timeout=60, timeout=60)
            client = Client(wsdl, transport=transport)
        except Exception as error:
            raise UserError(
                self.env._(
                    "Error connecting to AFIP webservice %(ws)s: %(error)s",
                    ws=self.afip_ws,
                    error=str(error),
                )
            ) from error

        if return_transport:
            return client, auth, transport
        return client, auth

    def connect(self):
        """
        Method to get a zeep client connected to the webservice.
        Returns a wrapper object that provides similar interface to pyafipws.
        """
        self.ensure_one()
        _logger.info(
            "Getting connection to ws %s on connection id %s", self.afip_ws, self.id
        )

        client, auth = self._get_client()

        # Return a wrapper object that provides similar interface
        return AfipWsClient(
            client=client,
            auth=auth,
            cuit=self.company_id.vat,
            token=self.token,
            sign=self.sign,
            afip_ws=self.afip_ws,
            connection=self,
        )


class AfipWsClient:
    """
    Wrapper class that provides a similar interface to pyafipws classes.
    This allows gradual migration of code that uses pyafipws.
    Implements WSFE, WSFEX, WSBFE methods using zeep.
    """

    def __init__(self, client, auth, cuit, token, sign, afip_ws, connection):
        self.client = client
        self.auth = auth
        self.Cuit = cuit
        self.Token = token
        self.Sign = sign
        self.afip_ws = afip_ws
        self.connection = connection

        # Response attributes (pyafipws compatibility)
        self.Obs = ""
        self.ErrMsg = ""
        self.Errores = []
        self.Excepcion = ""
        self.XmlRequest = ""
        self.XmlResponse = ""
        self.Resultado = ""
        self.CAE = ""
        self.CbteNro = 0
        self.FchVencCAE = ""
        self.Vencimiento = ""

        # Internal data storage for invoice building
        self._factura = {}
        self._ivas = []
        self._tributos = []
        self._cbtes_asoc = []
        self._opcionales = []
        self._items = []
        self._permisos = []

    def _call_ws(self, method_name, **kwargs):
        """
        Call a webservice method and capture request/response XML.
        """
        try:
            method = getattr(self.client.service, method_name)

            # Enable history plugin for XML capture
            from zeep.plugins import HistoryPlugin

            history = HistoryPlugin()

            # Recreate client with history plugin for this call
            # Use custom session with SSL adapter for AFIP compatibility
            session = _get_afip_session()
            transport = Transport(session=session, operation_timeout=60, timeout=60)
            client_with_history = Client(
                self.connection.afip_ws_url, transport=transport, plugins=[history]
            )
            method = getattr(client_with_history.service, method_name)
            result = method(**kwargs)

            # Capture XML
            if history.last_sent:
                self.XmlRequest = etree.tostring(
                    history.last_sent["envelope"], pretty_print=True, encoding="unicode"
                )
            if history.last_received:
                self.XmlResponse = etree.tostring(
                    history.last_received["envelope"],
                    pretty_print=True,
                    encoding="unicode",
                )

            return result
        except Exception as e:
            self.Excepcion = str(e)
            raise

    # ==================== WSFE Methods ====================

    def CrearFactura(self, **kwargs):
        """Store invoice header data for WSFE/WSFEX."""
        self._factura = kwargs
        # Reset arrays
        self._ivas = []
        self._tributos = []
        self._cbtes_asoc = []
        self._opcionales = []
        self._items = []
        self._permisos = []

    def AgregarIva(self, **kwargs):
        """Add VAT tax line for WSFE."""
        self._ivas.append(kwargs)

    def AgregarTributo(self, **kwargs):
        """Add other tax/tribute for WSFE."""
        self._tributos.append(kwargs)

    def AgregarCmpAsoc(self, **kwargs):
        """Add associated document."""
        self._cbtes_asoc.append(kwargs)

    def AgregarOpcional(self, **kwargs):
        """Add optional data for WSFE."""
        self._opcionales.append(kwargs)

    def AgregarItem(self, **kwargs):
        """Add item line for WSFEX."""
        self._items.append(kwargs)

    def AgregarPermiso(self, **kwargs):
        """Add export permit for WSFEX."""
        self._permisos.append(kwargs)

    def CAESolicitar(self):
        """
        Request CAE for domestic invoices (WSFE).
        Builds the SOAP request and sends it to AFIP.
        """
        try:
            # Build FECAERequest structure
            factura = self._factura

            # Build FeDetReq (detail)
            fe_det = {
                "Concepto": int(factura.get("concepto", 1)),
                "DocTipo": int(factura.get("tipo_doc", 99)),
                "DocNro": int(factura.get("nro_doc", 0))
                if factura.get("nro_doc")
                else 0,
                "CbteDesde": int(factura.get("cbt_desde", 1)),
                "CbteHasta": int(factura.get("cbt_hasta", 1)),
                "CbteFch": factura.get("fecha_cbte", ""),
                "ImpTotal": float(factura.get("imp_total", 0)),
                "ImpTotConc": float(factura.get("imp_tot_conc", 0)),
                "ImpNeto": float(factura.get("imp_neto", 0)),
                "ImpOpEx": float(factura.get("imp_op_ex", 0)),
                "ImpTrib": float(factura.get("imp_trib", 0)),
                "ImpIVA": float(factura.get("imp_iva", 0)),
                "MonId": factura.get("moneda_id", "PES"),
                "MonCotiz": float(factura.get("moneda_ctz", 1)),
            }

            # Add service dates if present
            if factura.get("fecha_serv_desde"):
                fe_det["FchServDesde"] = factura["fecha_serv_desde"]
            if factura.get("fecha_serv_hasta"):
                fe_det["FchServHasta"] = factura["fecha_serv_hasta"]
            if factura.get("fecha_venc_pago"):
                fe_det["FchVtoPago"] = factura["fecha_venc_pago"]

            # Add receiver's VAT condition (required from 01/02/2026 per RG 5616)
            if factura.get("condicion_iva_receptor"):
                fe_det["CondicionIVAReceptorId"] = int(
                    factura["condicion_iva_receptor"]
                )

            # Add IVA array
            if self._ivas:
                iva_array = []
                for iva in self._ivas:
                    iva_array.append(
                        {
                            "Id": int(iva.get("iva_id", 5)),
                            "BaseImp": float(iva.get("base_imp", 0)),
                            "Importe": float(iva.get("importe", 0)),
                        }
                    )
                fe_det["Iva"] = {"AlicIva": iva_array}

            # Add Tributos array
            if self._tributos:
                trib_array = []
                for trib in self._tributos:
                    trib_array.append(
                        {
                            "Id": int(trib.get("tributo_id", 99)),
                            "Desc": trib.get("ds", ""),
                            "BaseImp": float(trib.get("base_imp", 0)),
                            "Alic": float(trib.get("alic", 0)),
                            "Importe": float(trib.get("importe", 0)),
                        }
                    )
                fe_det["Tributos"] = {"Tributo": trib_array}

            # Add CbtesAsoc array
            if self._cbtes_asoc:
                asoc_array = []
                for asoc in self._cbtes_asoc:
                    asoc_array.append(
                        {
                            "Tipo": int(asoc.get("tipo", 0)),
                            "PtoVta": int(asoc.get("pto_vta", 0)),
                            "Nro": int(asoc.get("nro", 0)),
                            "Cuit": asoc.get("CUIT", ""),
                            "CbteFch": asoc.get("fecha", ""),
                        }
                    )
                fe_det["CbtesAsoc"] = {"CbteAsoc": asoc_array}

            # Add Opcionales array
            if self._opcionales:
                opt_array = []
                for opt in self._opcionales:
                    opt_array.append(
                        {
                            "Id": opt.get("id", ""),
                            "Valor": opt.get("valor", ""),
                        }
                    )
                fe_det["Opcionales"] = {"Opcional": opt_array}

            # Build FECAERequest
            fe_cae_req = {
                "FeCabReq": {
                    "CantReg": 1,
                    "PtoVta": int(factura.get("punto_vta", 1)),
                    "CbteTipo": int(factura.get("tipo_cbte", 1)),
                },
                "FeDetReq": {"FECAEDetRequest": [fe_det]},
            }

            # Build Auth
            auth = {
                "Token": self.Token,
                "Sign": self.Sign,
                "Cuit": int(self.Cuit) if self.Cuit else 0,
            }

            # Call WSFE
            _logger.info(
                "Calling FECAESolicitar for invoice %s", factura.get("cbte_nro")
            )
            result = self._call_ws("FECAESolicitar", Auth=auth, FeCAEReq=fe_cae_req)

            # Parse response
            self._parse_wsfe_response(result)

        except Exception as e:
            self.Excepcion = str(e)
            self.Resultado = "R"
            self.ErrMsg = str(e)
            _logger.error("CAESolicitar error: %s", str(e))
            raise

    def _parse_wsfe_response(self, result):  # noqa: C901
        """Parse WSFE FECAESolicitar response."""
        try:
            # Convert zeep response to dict for easier access
            if serialize_object:
                result_dict = serialize_object(result)
            else:
                result_dict = result

            # Get FECAEDetResponse
            fe_det_resp = None
            if isinstance(result_dict, dict):
                fe_det_resp = (result_dict.get("FeDetResp") or {}).get(
                    "FECAEDetResponse", []
                )
                if fe_det_resp and isinstance(fe_det_resp, list):
                    fe_det_resp = fe_det_resp[0]
            else:
                # Handle zeep object
                if hasattr(result, "FeDetResp") and result.FeDetResp:
                    if hasattr(result.FeDetResp, "FECAEDetResponse"):
                        responses = result.FeDetResp.FECAEDetResponse
                        if responses:
                            fe_det_resp = responses[0]

            if fe_det_resp:
                if isinstance(fe_det_resp, dict):
                    self.Resultado = fe_det_resp.get("Resultado", "R")
                    self.CAE = fe_det_resp.get("CAE", "")
                    self.FchVencCAE = fe_det_resp.get("CAEFchVto", "")
                    self.CbteNro = fe_det_resp.get("CbteDesde", 0)

                    # Get observations
                    obs = fe_det_resp.get("Observaciones") or {}
                    if obs:
                        obs_list = obs.get("Obs") or []
                        if obs_list:
                            self.Obs = "; ".join(
                                [
                                    f"{o.get('Code', '')}: {o.get('Msg', '')}"
                                    for o in obs_list
                                ]
                            )
                else:
                    # Handle zeep object
                    self.Resultado = getattr(fe_det_resp, "Resultado", "R")
                    self.CAE = getattr(fe_det_resp, "CAE", "") or ""
                    self.FchVencCAE = getattr(fe_det_resp, "CAEFchVto", "") or ""
                    self.CbteNro = getattr(fe_det_resp, "CbteDesde", 0) or 0

                    if (
                        hasattr(fe_det_resp, "Observaciones")
                        and fe_det_resp.Observaciones
                    ):
                        obs_list = fe_det_resp.Observaciones.Obs or []
                        self.Obs = "; ".join(
                            [
                                f"{getattr(o, 'Code', '')}: {getattr(o, 'Msg', '')}"
                                for o in obs_list
                            ]
                        )

            # Get errors from main response
            errors = None
            if isinstance(result_dict, dict):
                errors = (result_dict.get("Errors") or {}).get("Err") or []
            elif hasattr(result, "Errors") and result.Errors:
                errors = result.Errors.Err or []

            if errors:
                if isinstance(errors, list):
                    err_msgs = []
                    for e in errors:
                        if isinstance(e, dict):
                            code = e.get("Code", "")
                            msg = e.get("Msg", "")
                        else:
                            code = getattr(e, "Code", "")
                            msg = getattr(e, "Msg", "")
                        err_msgs.append(f"{code}: {msg}")
                    self.ErrMsg = "; ".join(err_msgs)
                else:
                    self.ErrMsg = str(errors)

            _logger.info(
                "WSFE Response - Resultado: %s, CAE: %s, CbteNro: %s, Obs: %s, Err: %s",
                self.Resultado,
                self.CAE,
                self.CbteNro,
                self.Obs,
                self.ErrMsg,
            )

        except Exception as e:
            _logger.error("Error parsing WSFE response: %s", str(e))
            self.Resultado = "R"
            self.ErrMsg = f"Error parsing response: {str(e)}"

    # ==================== WSFEX Methods ====================

    def Authorize(self, invoice_id):
        """
        Request authorization for export invoices (WSFEX).
        """
        try:
            factura = self._factura

            # Build Cmp (comprobante) structure for WSFEX
            cmp = {
                "Id": invoice_id,
                "Fecha_cbte": factura.get("fecha_cbte", ""),
                "Tipo_cbte": int(factura.get("tipo_cbte", 19)),
                "Punto_vta": int(factura.get("punto_vta", 1)),
                "Cbte_nro": int(factura.get("cbte_nro", 1)),
                "Tipo_expo": int(factura.get("tipo_expo", 1)),
                "Permiso_existente": factura.get("permiso_existente", "N"),
                "Pais_dst_cmp": int(factura.get("pais_dst_cmp", 0))
                if factura.get("pais_dst_cmp")
                else 0,
                "Nombre_cliente": factura.get("nombre_cliente", ""),
                "Cuit_pais_cliente": factura.get("cuit_pais_cliente") or None,
                "Domicilio_cliente": factura.get("domicilio_cliente", ""),
                "Id_impositivo": factura.get("id_impositivo") or None,
                "Moneda_Id": factura.get("moneda_id", "DOL"),
                "Moneda_ctz": float(factura.get("moneda_ctz", 1)),
                "Obs_comerciales": factura.get("obs_comerciales") or None,
                "Obs_generales": factura.get("obs_generales") or None,
                "Forma_pago": factura.get("forma_pago") or None,
                "Incoterms": factura.get("incoterms") or None,
                "Incoterms_Ds": factura.get("incoterms_ds") or None,
                "Idioma_cbte": int(factura.get("idioma_cbte", 1)),
                "Imp_total": float(factura.get("imp_total", 0)),
            }

            # Add items
            if self._items:
                items_array = []
                for item in self._items:
                    items_array.append(
                        {
                            "Pro_codigo": item.get("codigo") or "",
                            "Pro_ds": item.get("ds", ""),
                            "Pro_qty": float(item.get("qty", 1)),
                            "Pro_umed": int(item.get("umed", 7)),
                            "Pro_precio_uni": float(item.get("precio", 0)),
                            "Pro_total_item": float(item.get("importe", 0)),
                            "Pro_bonificacion": float(item.get("bonif", 0))
                            if item.get("bonif")
                            else 0,
                        }
                    )
                cmp["Items"] = {"Item": items_array}

            # Add CbtesAsoc
            if self._cbtes_asoc:
                asoc_array = []
                for asoc in self._cbtes_asoc:
                    asoc_array.append(
                        {
                            "Cbte_tipo": int(asoc.get("tipo", 0)),
                            "Cbte_punto_vta": int(asoc.get("pto_vta", 0)),
                            "Cbte_nro": int(asoc.get("nro", 0)),
                            "Cbte_cuit": asoc.get("CUIT", ""),
                        }
                    )
                cmp["Cmps_asoc"] = {"Cmp_asoc": asoc_array}

            # Add Permisos
            if self._permisos:
                perm_array = []
                for perm in self._permisos:
                    perm_array.append(
                        {
                            "Id_permiso": perm.get("id_permiso", ""),
                            "Dst_merc": int(perm.get("dst_merc", 0)),
                        }
                    )
                cmp["Permisos"] = {"Permiso": perm_array}

            # Build Auth
            auth = {
                "Token": self.Token,
                "Sign": self.Sign,
                "Cuit": int(self.Cuit) if self.Cuit else 0,
            }

            # Call WSFEX
            _logger.info("Calling FEXAuthorize for invoice %s", factura.get("cbte_nro"))
            result = self._call_ws("FEXAuthorize", Auth=auth, Cmp=cmp)

            # Parse response
            self._parse_wsfex_response(result)

        except Exception as e:
            self.Excepcion = str(e)
            self.Resultado = "R"
            self.ErrMsg = str(e)
            _logger.error("WSFEX Authorize error: %s", str(e))
            raise

    def _parse_wsfex_response(self, result):
        """Parse WSFEX FEXAuthorize response."""
        try:
            if serialize_object:
                result_dict = serialize_object(result)
            else:
                result_dict = result

            # Get FEXResultAuth
            auth_resp = None
            if isinstance(result_dict, dict):
                auth_resp = result_dict.get("FEXResultAuth") or {}
            elif hasattr(result, "FEXResultAuth"):
                auth_resp = result.FEXResultAuth

            if auth_resp:
                if isinstance(auth_resp, dict):
                    self.Resultado = auth_resp.get("Resultado", "R")
                    self.CAE = auth_resp.get("Cae", "")
                    self.Vencimiento = auth_resp.get("Fch_venc_Cae", "")
                    self.FchVencCAE = self.Vencimiento
                    self.CbteNro = auth_resp.get("Cbte_nro", 0)
                    self.Obs = auth_resp.get("Obs", "") or ""
                else:
                    self.Resultado = getattr(auth_resp, "Resultado", "R")
                    self.CAE = getattr(auth_resp, "Cae", "") or ""
                    self.Vencimiento = getattr(auth_resp, "Fch_venc_Cae", "") or ""
                    self.FchVencCAE = self.Vencimiento
                    self.CbteNro = getattr(auth_resp, "Cbte_nro", 0) or 0
                    self.Obs = getattr(auth_resp, "Obs", "") or ""

            # Get errors
            err_resp = None
            if isinstance(result_dict, dict):
                err_resp = result_dict.get("FEXErr") or {}
            elif hasattr(result, "FEXErr"):
                err_resp = result.FEXErr

            if err_resp:
                if isinstance(err_resp, dict):
                    err_code = err_resp.get("ErrCode", 0)
                    err_msg = err_resp.get("ErrMsg", "")
                else:
                    err_code = getattr(err_resp, "ErrCode", 0)
                    err_msg = getattr(err_resp, "ErrMsg", "")
                if err_code and err_code != 0:
                    self.ErrMsg = f"{err_code}: {err_msg}"

            _logger.info(
                "WSFEX Response - Resultado: %s, CAE: %s, CbteNro: %s, Vencimiento: %s",
                self.Resultado,
                self.CAE,
                self.CbteNro,
                self.Vencimiento,
            )

        except Exception as e:
            _logger.error("Error parsing WSFEX response: %s", str(e))
            self.Resultado = "R"
            self.ErrMsg = f"Error parsing response: {str(e)}"

    # ==================== Utility Methods ====================

    def CompUltimoAutorizado(self, tipo_cbte, punto_vta):
        """
        Get last authorized invoice number for WSFE.
        """
        try:
            auth = {
                "Token": self.Token,
                "Sign": self.Sign,
                "Cuit": int(self.Cuit) if self.Cuit else 0,
            }

            result = self._call_ws(
                "FECompUltimoAutorizado",
                Auth=auth,
                PtoVta=int(punto_vta),
                CbteTipo=int(tipo_cbte),
            )

            if serialize_object:
                result_dict = serialize_object(result)
            else:
                result_dict = result

            if isinstance(result_dict, dict):
                return result_dict.get("CbteNro", 0)
            else:
                return getattr(result, "CbteNro", 0) or 0

        except Exception as e:
            _logger.error("CompUltimoAutorizado error: %s", str(e))
            return 0

    def GetLastCMP(self, tipo_cbte, punto_vta):
        """
        Get last invoice number for WSFEX.
        """
        try:
            auth = {
                "Token": self.Token,
                "Sign": self.Sign,
                "Cuit": int(self.Cuit) if self.Cuit else 0,
            }

            result = self._call_ws(
                "FEXGetLast_CMP",
                Auth=auth,
                Pto_venta=int(punto_vta),
                Cbte_Tipo=int(tipo_cbte),
            )

            if serialize_object:
                result_dict = serialize_object(result)
            else:
                result_dict = result

            last_cmp = None
            if isinstance(result_dict, dict):
                last_cmp = result_dict.get("FEXResult_LastCMP", {})
            elif hasattr(result, "FEXResult_LastCMP"):
                last_cmp = result.FEXResult_LastCMP

            if last_cmp:
                if isinstance(last_cmp, dict):
                    return last_cmp.get("Cbte_nro", 0)
                else:
                    return getattr(last_cmp, "Cbte_nro", 0) or 0
            return 0

        except Exception as e:
            _logger.error("GetLastCMP error: %s", str(e))
            return 0

    # ==================== Dummy/Status Methods ====================

    def Dummy(self):
        """
        Test AFIP service availability.
        Sets AppServerStatus, DbServerStatus, AuthServerStatus attributes.
        """
        self.AppServerStatus = ""
        self.DbServerStatus = ""
        self.AuthServerStatus = ""

        try:
            # Different webservices have different dummy methods
            if self.afip_ws == "wsfe":
                result = self._call_ws("FEDummy")
            elif self.afip_ws == "wsfex":
                result = self._call_ws("FEXDummy")
            elif self.afip_ws == "wsbfe":
                result = self._call_ws("BFEDummy")
            else:
                # Generic attempt
                result = self._call_ws("Dummy")

            if serialize_object:
                result_dict = serialize_object(result)
            else:
                result_dict = result

            if isinstance(result_dict, dict):
                self.AppServerStatus = result_dict.get("AppServer", "")
                self.DbServerStatus = result_dict.get("DbServer", "")
                self.AuthServerStatus = result_dict.get("AuthServer", "")
            else:
                self.AppServerStatus = getattr(result, "AppServer", "") or ""
                self.DbServerStatus = getattr(result, "DbServer", "") or ""
                self.AuthServerStatus = getattr(result, "AuthServer", "") or ""

        except Exception as e:
            _logger.error("Dummy error: %s", str(e))
            self.Excepcion = str(e)

    # ==================== Parameter Query Methods ====================

    def ParamGetTiposCbte(self, sep=","):
        """
        Get available document types for WSFE.
        """
        try:
            auth = {
                "Token": self.Token,
                "Sign": self.Sign,
                "Cuit": int(self.Cuit) if self.Cuit else 0,
            }

            result = self._call_ws("FEParamGetTiposCbte", Auth=auth)

            if serialize_object:
                result_dict = serialize_object(result)
            else:
                result_dict = result

            ret = []
            tipos = None
            if isinstance(result_dict, dict):
                tipos = result_dict.get("ResultGet", {}).get("CbteTipo", [])
            elif hasattr(result, "ResultGet") and result.ResultGet:
                tipos = result.ResultGet.CbteTipo or []

            for tipo in tipos or []:
                if isinstance(tipo, dict):
                    ret.append(f"{tipo.get('Id', '')}{sep}{tipo.get('Desc', '')}")
                else:
                    ret.append(
                        f"{getattr(tipo, 'Id', '')}{sep}{getattr(tipo, 'Desc', '')}"
                    )
            return ret

        except Exception as e:
            _logger.error("ParamGetTiposCbte error: %s", str(e))
            self.Excepcion = str(e)
            return []

    def GetParamTipoCbte(self, sep=","):
        """
        Get available document types for WSFEX.
        """
        try:
            auth = {
                "Token": self.Token,
                "Sign": self.Sign,
                "Cuit": int(self.Cuit) if self.Cuit else 0,
            }

            result = self._call_ws("FEXGetPARAM_Cbte_Tipo", Auth=auth)

            if serialize_object:
                result_dict = serialize_object(result)
            else:
                result_dict = result

            ret = []
            tipos = None
            if isinstance(result_dict, dict):
                tipos = result_dict.get("FEXResultGet", {}).get(
                    "ClsFEXResponse_Cbte_Tipo", []
                )
            elif hasattr(result, "FEXResultGet") and result.FEXResultGet:
                tipos = result.FEXResultGet.ClsFEXResponse_Cbte_Tipo or []

            for tipo in tipos or []:
                if isinstance(tipo, dict):
                    ret.append(
                        f"{tipo.get('Cbte_Id', '')}{sep}{tipo.get('Cbte_Ds', '')}"
                    )
                else:
                    cbte_id = getattr(tipo, "Cbte_Id", "")
                    cbte_ds = getattr(tipo, "Cbte_Ds", "")
                    ret.append(f"{cbte_id}{sep}{cbte_ds}")
            return ret

        except Exception as e:
            _logger.error("GetParamTipoCbte error: %s", str(e))
            self.Excepcion = str(e)
            return []

    def ParamGetPtosVenta(self, sep=" "):
        """
        Get available points of sale for WSFE.
        """
        try:
            auth = {
                "Token": self.Token,
                "Sign": self.Sign,
                "Cuit": int(self.Cuit) if self.Cuit else 0,
            }

            result = self._call_ws("FEParamGetPtosVenta", Auth=auth)

            if serialize_object:
                result_dict = serialize_object(result)
            else:
                result_dict = result

            ret = []
            ptos = None
            if isinstance(result_dict, dict):
                ptos = result_dict.get("ResultGet", {}).get("PtoVenta", [])
            elif hasattr(result, "ResultGet") and result.ResultGet:
                ptos = result.ResultGet.PtoVenta or []

            for pto in ptos or []:
                if isinstance(pto, dict):
                    nro = pto.get("Nro", "")
                    emision = pto.get("EmisionTipo", "")
                else:
                    nro = getattr(pto, "Nro", "")
                    emision = getattr(pto, "EmisionTipo", "")
                ret.append(f"{nro}{sep}{emision}")
            return ret

        except Exception as e:
            _logger.error("ParamGetPtosVenta error: %s", str(e))
            self.Excepcion = str(e)
            return []

    def GetParamPtosVenta(self):
        """
        Get available points of sale for WSFEX.
        """
        try:
            auth = {
                "Token": self.Token,
                "Sign": self.Sign,
                "Cuit": int(self.Cuit) if self.Cuit else 0,
            }

            result = self._call_ws("FEXGetPARAM_PtoVenta", Auth=auth)

            if serialize_object:
                result_dict = serialize_object(result)
            else:
                result_dict = result

            ret = []
            ptos = None
            if isinstance(result_dict, dict):
                ptos = result_dict.get("FEXResultGet", {}).get(
                    "ClsFEXResponse_PtoVenta", []
                )
            elif hasattr(result, "FEXResultGet") and result.FEXResultGet:
                ptos = result.FEXResultGet.ClsFEXResponse_PtoVenta or []

            for pto in ptos or []:
                if isinstance(pto, dict):
                    ret.append(f"{pto.get('Pto_venta', '')}")
                else:
                    ret.append(f"{getattr(pto, 'Pto_venta', '')}")
            return ret

        except Exception as e:
            _logger.error("GetParamPtosVenta error: %s", str(e))
            self.Excepcion = str(e)
            return []

    def GetParamNCM(self):
        """
        Get NCM (Nomenclatura Común del Mercosur) codes for WSBFE.
        """
        try:
            auth = {
                "Token": self.Token,
                "Sign": self.Sign,
                "Cuit": int(self.Cuit) if self.Cuit else 0,
            }

            result = self._call_ws("BFEGetPARAM_NCM", Auth=auth)

            if serialize_object:
                result_dict = serialize_object(result)
            else:
                result_dict = result

            ret = []
            ncms = None
            if isinstance(result_dict, dict):
                ncms = result_dict.get("BFEResultGet", {}).get("ClsBFEResponse_NCM", [])
            elif hasattr(result, "BFEResultGet") and result.BFEResultGet:
                ncms = getattr(result.BFEResultGet, "ClsBFEResponse_NCM", []) or []

            for ncm in ncms or []:
                if isinstance(ncm, dict):
                    codigo = ncm.get("NCM_Codigo", "")
                    desc = ncm.get("NCM_Ds", "")
                else:
                    codigo = getattr(ncm, "NCM_Codigo", "")
                    desc = getattr(ncm, "NCM_Ds", "")
                ret.append(f"{codigo} - {desc}")
            return ret

        except Exception as e:
            _logger.error("GetParamNCM error: %s", str(e))
            self.Excepcion = str(e)
            return []

    def GetParamZonas(self):
        """
        Get zones for WSBFE.
        """
        try:
            auth = {
                "Token": self.Token,
                "Sign": self.Sign,
                "Cuit": int(self.Cuit) if self.Cuit else 0,
            }

            result = self._call_ws("BFEGetPARAM_Zonas", Auth=auth)

            if serialize_object:
                result_dict = serialize_object(result)
            else:
                result_dict = result

            ret = []
            zonas = None
            if isinstance(result_dict, dict):
                zonas = result_dict.get("BFEResultGet", {}).get(
                    "ClsBFEResponse_Zona", []
                )
            elif hasattr(result, "BFEResultGet") and result.BFEResultGet:
                zonas = getattr(result.BFEResultGet, "ClsBFEResponse_Zona", []) or []

            for zona in zonas or []:
                if isinstance(zona, dict):
                    codigo = zona.get("Zona_Codigo", "")
                    desc = zona.get("Zona_Ds", "")
                else:
                    codigo = getattr(zona, "Zona_Codigo", "")
                    desc = getattr(zona, "Zona_Ds", "")
                ret.append(f"{codigo} - {desc}")
            return ret

        except Exception as e:
            _logger.error("GetParamZonas error: %s", str(e))
            self.Excepcion = str(e)
            return []
