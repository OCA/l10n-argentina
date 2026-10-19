# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

import base64
import datetime
import logging
import ssl
import time

from lxml import builder, etree

from odoo import api, fields, models
from odoo.exceptions import UserError

try:
    from requests import Session
    from zeep import Client, Transport
except ImportError:
    # For Odoo 19, zeep might be in odoo.tools
    try:
        from requests import Session

        from odoo.tools.zeep import Client, Transport
    except ImportError:
        Client = None
        Transport = None
        Session = None

_logger = logging.getLogger(__name__)


def _get_afip_ssl_context():
    """
    Create SSL context that works with AFIP servers.
    AFIP uses weak DH keys that require lowering security level.
    """
    ctx = ssl.create_default_context()
    # Lower security level to allow AFIP's weak DH keys
    ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    return ctx


class ResCompany(models.Model):
    _inherit = "res.company"

    afip_ws_env_type = fields.Selection(
        [("homologation", "Homologation"), ("production", "Production")],
        string="AFIP WS Environment",
        default="production",
        help="Environment is used to connect AFIP Web Services.\n"
        "Production: This is the connection used in real world.\n"
        "Homologation: Use this environment to test AFIP Web Services.",
    )

    alias_ids = fields.One2many(
        "afipws.certificate_alias",
        "company_id",
        "Aliases",
    )
    connection_ids = fields.One2many(
        "afipws.connection",
        "company_id",
        "Connections",
    )

    def _get_certificate(self, environment_type):
        """
        Get confirmed certificate for the given environment type.
        """
        self.ensure_one()
        certificate = self.env["afipws.certificate"].search(
            [
                ("alias_id.company_id", "=", self.id),
                ("alias_id.type", "=", environment_type),
                ("state", "=", "confirmed"),
            ],
            limit=1,
        )
        if not certificate:
            raise UserError(
                self.env._(
                    'No confirmed certificate for "%(environment_type)s" '
                    'on company "%(name)s"',
                    environment_type=environment_type,
                    name=self.name,
                )
            )
        if (
            len(
                self.env["afipws.certificate"].search(
                    [
                        ("alias_id.company_id", "=", self.id),
                        ("alias_id.type", "=", environment_type),
                        ("state", "=", "confirmed"),
                    ]
                )
            )
            > 1
        ):
            raise UserError(
                self.env._(
                    'Multiple confirmed certificates for "%(environment_type)s" found. '
                    "Please keep only one confirmed certificate.",
                    environment_type=environment_type,
                )
            )
        return certificate

    def get_connection(self, afip_ws):
        """Get or create a valid connection for the given webservice."""
        self.ensure_one()
        _logger.info(f"Getting connection for company {self.name} and ws {afip_ws}")
        now = fields.Datetime.now()
        environment_type = self.afip_ws_env_type

        connection = self.connection_ids.search(
            [
                ("type", "=", environment_type),
                ("generationtime", "<=", now),
                ("expirationtime", ">", now),
                ("afip_ws", "=", afip_ws),
                ("company_id", "=", self.id),
            ],
            limit=1,
        )
        if not connection:
            connection = self._create_connection(afip_ws, environment_type)
        return connection

    def _create_connection(self, afip_ws, environment_type):
        """
        Create a new connection by authenticating with AFIP using zeep.
        """
        self.ensure_one()
        _logger.info(
            "Creating connection for company %s, environment %s, ws %s",
            self.name,
            environment_type,
            afip_ws,
        )

        certificate = self._get_certificate(environment_type)

        # Build login ticket request (TRA)
        generation_time = fields.Datetime.now()
        expiration_time = fields.Datetime.add(generation_time, hours=12)
        unique_id = str(int(time.mktime(datetime.datetime.now().timetuple())))

        request_xml = builder.E.loginTicketRequest(
            {"version": "1.0"},
            builder.E.header(
                builder.E.uniqueId(unique_id),
                builder.E.generationTime(
                    generation_time.strftime("%Y-%m-%dT%H:%M:%S-00:00")
                ),
                builder.E.expirationTime(
                    expiration_time.strftime("%Y-%m-%dT%H:%M:%S-00:00")
                ),
            ),
            builder.E.service(afip_ws),
        )
        request = etree.tostring(request_xml, pretty_print=True)

        # Sign the request using PKCS7
        signed_request = certificate.pkcs7_sign(request)

        # Get WSAA URL
        wsdl = self._get_wsaa_url(environment_type)

        try:
            _logger.info("Connecting to AFIP WSAA: %s for ws %s", wsdl, afip_ws)
            # Create session with custom SSL context for AFIP compatibility
            session = Session()
            session.verify = True
            # Mount custom SSL adapter
            from requests.adapters import HTTPAdapter
            from urllib3.util.ssl_ import create_urllib3_context

            class AFIPHTTPAdapter(HTTPAdapter):
                def init_poolmanager(self, *args, **kwargs):
                    ctx = create_urllib3_context()
                    ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
                    kwargs["ssl_context"] = ctx
                    return super().init_poolmanager(*args, **kwargs)

            session.mount("https://", AFIPHTTPAdapter())
            transport = Transport(session=session, operation_timeout=60, timeout=60)
            client = Client(wsdl, transport=transport)
            response = client.service.loginCms(
                base64.b64encode(signed_request).decode()
            )
        except Exception as error:
            self._process_connection_error(error, environment_type, afip_ws)

        # Parse response
        response_xml = etree.fromstring(response.encode("utf-8"))
        token = response_xml.xpath("/loginTicketResponse/credentials/token")[0].text
        sign = response_xml.xpath("/loginTicketResponse/credentials/sign")[0].text

        # Create connection record
        auth_data = {
            "uniqueid": unique_id,
            "generationtime": generation_time,
            "expirationtime": expiration_time,
            "token": token,
            "sign": sign,
            "company_id": self.id,
            "afip_ws": afip_ws,
            "type": environment_type,
        }

        _logger.info("Successful connection to AFIP for ws %s", afip_ws)
        return self.connection_ids.create(auth_data)

    @api.model
    def _get_wsaa_url(self, environment_type):
        """Get WSAA authentication service URL."""
        urls = {
            "production": "https://wsaa.afip.gov.ar/ws/services/LoginCms?WSDL",
            "homologation": "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?WSDL",
        }
        return urls.get(environment_type)

    @api.model
    def _process_connection_error(self, error, env_type, afip_ws):
        """Process and raise user-friendly connection errors."""
        if hasattr(error, "message"):
            error_name = error.message
        else:
            error_name = str(error)

        error_msg = self.env._(
            "Connection error to %(webservice)s webservice: %(error)s",
            webservice=afip_ws,
            error=error_name,
        )

        # Provide hints for common errors
        hints = {
            "Computador no autorizado": self.env._(
                "The certificate is not authorized for this webservice"
            ),
            "cms.sign.invalid": self.env._("Invalid signature or expired certificate"),
            "cms.cert.expired": self.env._("Certificate has expired"),
            "500 Server Error": self.env._("AFIP webservice is down"),
            "No se puede decodificar": self.env._(
                "Certificate and private key do not match"
            ),
        }

        for key, hint in hints.items():
            if key in error_name:
                error_msg += "\n\nHINT: " + hint
                break

        raise UserError(error_msg)

    # Keep backward compatibility method
    def get_key_and_certificate(self, environment_type):
        """
        Legacy method for backward compatibility.
        Returns (private_key, certificate) tuple.
        """
        self.ensure_one()
        certificate = self._get_certificate(environment_type)
        return (certificate.alias_id.key, certificate.crt)
