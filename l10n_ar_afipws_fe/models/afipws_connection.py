# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AfipwsConnection(models.Model):
    _inherit = "afipws.connection"

    afip_ws = fields.Selection(
        default="wsfe",
        selection_add=[
            ("wsfe", "Mercado interno -sin detalle- RG2485 (WSFEv1)"),
            ("wsmtxca", "Mercado interno -con detalle- RG2904 (WSMTXCA)"),
            ("wsfex", "Exportacion -con detalle- RG2758 (WSFEXv1)"),
            ("wsbfe", "Bono Fiscal -con detalle- RG2557 (WSBFE)"),
            ("wscdc", "Constatacion de Comprobantes (WSCDC)"),
        ],
        ondelete={
            "wsfe": "set default",
            "wsmtxca": "set default",
            "wsfex": "set default",
            "wsbfe": "set default",
            "wscdc": "set default",
        },
    )

    @api.model
    def get_afip_ws_url(self, afip_ws, environment_type):
        """
        Extend base method to add electronic invoice webservice URLs.
        """
        afip_ws_url = super().get_afip_ws_url(afip_ws, environment_type)
        if afip_ws_url:
            return afip_ws_url

        # Electronic invoice webservice URLs
        ws_urls = {
            "wsfe": {
                "production": "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL",
                "homologation": "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL",
            },
            "wsfex": {
                "production": "https://servicios1.afip.gov.ar/wsfexv1/service.asmx?WSDL",
                "homologation": "https://wswhomo.afip.gov.ar/wsfexv1/service.asmx?WSDL",
            },
            "wsbfe": {
                "production": "https://servicios1.afip.gov.ar/wsbfev1/service.asmx?WSDL",
                "homologation": "https://wswhomo.afip.gov.ar/wsbfev1/service.asmx?WSDL",
            },
            "wscdc": {
                "production": "https://servicios1.afip.gov.ar/WSCDC/service.asmx?WSDL",
                "homologation": "https://wswhomo.afip.gov.ar/WSCDC/service.asmx?WSDL",
            },
            "wsmtxca": {
                "production": None,  # Not implemented
                "homologation": None,
            },
        }

        url = ws_urls.get(afip_ws, {}).get(environment_type)
        if afip_ws == "wsmtxca" and not url:
            raise UserError(
                self.env._("AFIP WS %(ws)s is not implemented yet", ws=afip_ws)
            )

        return url
