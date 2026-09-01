# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files


import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10nLatamDocumentType(models.Model):
    _inherit = "l10n_latam.document.type"

    journal_id = fields.Many2one("account.journal", "Journal")
    afip_ws = fields.Selection(related="journal_id.afip_ws")

    def get_pyafipws_consult_invoice(self, document_number):
        self.ensure_one()
        document_type = self.document_type_id.code
        company = self.journal_id.company_id
        afip_ws = self.journal_id.afip_ws
        if not afip_ws:
            raise UserError(
                self.env._(
                    "No AFIP WS selected on point of sale %(pos)s",
                    pos=self.journal_id.name,
                )
            )
        ws = company.get_connection(afip_ws).connect()
        if afip_ws in ("wsfe", "wsmtxca"):
            ws.CompConsultar(
                document_type, self.journal_id.point_of_sale_number, document_number
            )
            attributes = [
                "FechaCbte",
                "CbteNro",
                "PuntoVenta",
                "Vencimiento",
                "ImpTotal",
                "Resultado",
                "CbtDesde",
                "CbtHasta",
                "ImpTotal",
                "ImpNeto",
                "ImptoLiq",
                "ImpOpEx",
                "ImpTrib",
                "EmisionTipo",
                "CAE",
                "CAEA",
                "XmlResponse",
            ]
        elif afip_ws == "wsfex":
            ws.GetCMP(
                document_type, self.journal_id.point_of_sale_number, document_number
            )
            attributes = [
                "PuntoVenta",
                "CbteNro",
                "FechaCbte",
                "ImpTotal",
                "CAE",
                "Vencimiento",
                "FchVencCAE",
                "Resultado",
                "XmlResponse",
            ]
        elif afip_ws == "wsbfe":
            ws.GetCMP(
                document_type, self.journal_id.point_of_sale_number, document_number
            )
            attributes = [
                "PuntoVenta",
                "CbteNro",
                "FechaCbte",
                "ImpTotal",
                "ImptoLiq",
                "CAE",
                "Vencimiento",
                "FchVencCAE",
                "Resultado",
                "XmlResponse",
            ]
        else:
            raise UserError(self.env._("AFIP WS %(ws)s not implemented", ws=afip_ws))
        msg = ""
        title = self.env._("Invoice number %(number)s\n", number=document_number)

        # TODO ver como hacer para que tome los enter en los mensajes
        for pu_attrin in attributes:
            msg += f"{pu_attrin}: {getattr(ws, pu_attrin)}\n"

        msg += " - ".join([ws.Excepcion, ws.ErrMsg, ws.Obs])
        # TODO parsear este response. buscar este metodo que puede ayudar
        # b = ws.ObtenerTagXml("CAE")
        # import xml.etree.ElementTree as ET
        # T = ET.fromstring(ws.XmlResponse)

        _logger.info(f"{title}\n{msg}")
        raise UserError(title + msg)
