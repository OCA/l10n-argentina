##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

from odoo import _, fields, models
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
                _("No AFIP WS selected on point of sale %s") % (self.journal_id.name)
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
            raise UserError(_("AFIP WS %s not implemented") % afip_ws)
        msg = ""
        title = _("Invoice number %s\n" % document_number)

        # TODO ver como hacer para que tome los enter en los mensajes
        for pu_attrin in attributes:
            msg += "%s: %s\n" % (pu_attrin, getattr(ws, pu_attrin))

        msg += " - ".join([ws.Excepcion, ws.ErrMsg, ws.Obs])
        # TODO parsear este response. buscar este metodo que puede ayudar
        # b = ws.ObtenerTagXml("CAE")
        # import xml.etree.ElementTree as ET
        # T = ET.fromstring(ws.XmlResponse)

        _logger.info("%s\n%s" % (title, msg))
        raise UserError(title + msg)

    def get_last_invoice_number(self, invoice=None):
        if invoice:
            pos_number = invoice.journal_id.l10n_ar_afip_pos_number
            document_type = invoice.l10n_latam_document_type_id.code
            company = invoice.journal_id.company_id
            afip_ws = invoice.journal_id.afip_ws
        if not afip_ws:
            raise UserError(
                _(
                    "Can't determine afip_ws to use in journal %s"
                    % invoice.journal_id.name
                )
            )
        # Call webservice instance
        ws = company.get_connection(afip_ws).connect()
        try:
            if afip_ws in ("wsfe", "wsmtxca"):
                last_cbte = ws.CompUltimoAutorizado(document_type, pos_number)
            elif afip_ws in ["wsfex", "wsbfe"]:
                last_cbte = ws.GetLastCMP(document_type, pos_number)
            else:
                return _("AFIP WS %s not implemented") % afip_ws
        except ValueError as error:
            _logger.warning("exception in get_pyafipws_last_invoice: %s" % (str(error)))
            if "The read operation timed out" in str(error):
                raise UserError(_("Servicio AFIP Ocupado reintente en unos minutos"))
            else:
                raise UserError(
                    _(
                        "Hubo un error al conectarse a AFIP, contacte a su"
                        " administrador de sistemas"
                    )
                )
        return int(last_cbte)
