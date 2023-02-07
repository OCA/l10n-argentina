# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    afip_ws = fields.Selection(
        [
            ("wsfe", "Mercado interno -sin detalle- RG2485 (WSFEv1)"),
            ("wsmtxca", "Mercado interno -con detalle- RG2904 (WSMTXCA)"),
            ("wsfex", "Exportación -con detalle- RG2758 (WSFEXv1)"),
            ("wsbfe", "Bono Fiscal -con detalle- RG2557 (WSBFE)"),
        ],
        "Webservice AFIP",
        readonly="True",
        compute="_compute_afip_webservice",
        store=True,
    )

    @api.depends("l10n_ar_afip_pos_system")
    def _compute_afip_webservice(self):
        for record in self:
            if record.l10n_ar_afip_pos_system == "RLI_RLM":
                record.afip_ws = "wsfe"
            elif record.l10n_ar_afip_pos_system == "FEERCEL":
                self.afip_ws = "wsfex"
            elif record.l10n_ar_afip_pos_system == "CPERCEL":
                record.afip_ws = "wsmtxca"
            elif record.l10n_ar_afip_pos_system == "BFERCEL":
                record.afip_ws = "wsbfe"
            else:
                record.afip_ws = None

    def get_pyafipws_last_invoice(self, document_type):
        self.ensure_one()
        company = self.company_id
        afip_ws = self.afip_ws
        if not afip_ws:
            return _("No AFIP WS selected on point of sale %s") % (self.name)
        ws = company.get_connection(afip_ws).connect()
        # call the webservice method to get the last invoice at AFIP:
        try:
            if hasattr(self, "%s_get_pyafipws_last_invoice" % afip_ws):
                last = getattr(self, "%s_get_pyafipws_last_invoice" % afip_ws)(
                    self.l10n_ar_afip_pos_number, document_type, ws
                )
                _logger.info("AFIP Auth - Get last AFIP Number: %s" % last)
            else:
                return _("AFIP WS %s not implemented") % afip_ws
            return last
        except ValueError as error:
            _logger.warning("exception in get_pyafipws_last_invoice: %s" % (str(error)))
            if "The read operation timed out" in str(error):
                raise UserError(_("Servicio AFIP Ocupado reintente en unos minutos"))
            else:
                raise UserError(
                    _(
                        "Hubo un error al conectarse a AFIP, contacte a su"
                        " proveedor de Odoo para mas información"
                    )
                )

    def wsfe_get_pyafipws_last_invoice(
        self, l10n_ar_afip_pos_number, document_type, ws
    ):
        return ws.CompUltimoAutorizado(document_type.code, l10n_ar_afip_pos_number)

    def wsmtxca_get_pyafipws_last_invoice(
        self, l10n_ar_afip_pos_number, document_type, ws
    ):
        return ws.CompUltimoAutorizado(document_type.code, l10n_ar_afip_pos_number)

    def wsfex_get_pyafipws_last_invoice(
        self, l10n_ar_afip_pos_number, document_type, ws
    ):
        return ws.GetLastCMP(document_type.code, l10n_ar_afip_pos_number)

    def wsbfe_get_pyafipws_last_invoice(
        self, l10n_ar_afip_pos_number, document_type, ws
    ):
        return ws.GetLastCMP(document_type.code, l10n_ar_afip_pos_number)

    def test_pyafipws_dummy(self):
        """
        AFIP Description: Método Dummy para verificación de funcionamiento de
        infraestructura (FEDummy)
        """
        self.ensure_one()
        if self.l10n_ar_afip_pos_system != "FEERCEL":
            afip_ws = self.afip_ws
        else:
            afip_ws = "wsfex"
        if not afip_ws:
            raise UserError(_("No AFIP WS selected"))
        ws = self.company_id.get_connection(afip_ws).connect()
        ws.Dummy()
        title = _("AFIP service %s\n") % afip_ws
        msg = "AppServerStatus: %s DbServerStatus: %s AuthServerStatus: %s" % (
            ws.AppServerStatus,
            ws.DbServerStatus,
            ws.AuthServerStatus,
        )
        raise UserError(title + msg)

    def test_pyafipws_taxes(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_("No AFIP WS selected"))
        ws = self.company_id.get_connection(afip_ws).connect()
        ret = ws.ParamGetTiposTributos(sep="")
        msg = _(" %s %s") % (
            ". ".join(ret),
            " - ".join([ws.Excepcion, ws.ErrMsg, ws.Obs]),
        )
        title = _("Tributos en AFIP\n")
        raise UserError(title + msg)

    def test_pyafipws_point_of_sales(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_("No AFIP WS selected"))
        ws = self.company_id.get_connection(afip_ws).connect()
        if afip_ws == "wsfex":
            ret = ws.GetParamPtosVenta()
        elif afip_ws == "wsfe":
            ret = ws.ParamGetPtosVenta(sep=" ")
        else:
            raise UserError(
                _("Get point of sale for ws %s is not implemented yet") % (afip_ws)
            )
        msg = _(" %s %s") % (
            ". ".join(ret),
            " - ".join([ws.Excepcion, ws.ErrMsg, ws.Obs]),
        )
        title = _("Enabled Point Of Sales on AFIP\n")
        raise UserError(title + msg)

    def get_pyafipws_cuit_document_classes(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_("No AFIP WS selected"))
        ws = self.company_id.get_connection(afip_ws).connect()
        if afip_ws == "wsfex":
            ret = ws.GetParamTipoCbte(sep=",")
        elif afip_ws == "wsfe":
            ret = ws.ParamGetTiposCbte(sep=",")
        elif afip_ws == "wsbfe":
            ret = ws.GetParamTipoCbte()
        else:
            raise UserError(
                _("Get document types for ws %s is not implemented yet") % (afip_ws)
            )
        msg = _("Authorized Document Clases on AFIP\n%s\n. \nObservations: %s") % (
            "\n ".join(ret),
            ".\n".join([ws.Excepcion, ws.ErrMsg, ws.Obs]),
        )
        raise UserError(msg)

    def get_pyafipws_zonas(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_("No AFIP WS selected"))
        ws = self.company_id.get_connection(afip_ws).connect()
        if afip_ws == "wsbfe":
            ret = ws.GetParamZonas()
        else:
            raise UserError(_("Get zonas for ws %s is not implemented yet") % (afip_ws))
        msg = _("Zonas on AFIP\n%s\n. \nObservations: %s") % (
            "\n ".join(ret),
            ".\n".join([ws.Excepcion, ws.ErrMsg, ws.Obs]),
        )
        raise UserError(msg)

    def get_pyafipws_NCM(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_("No AFIP WS selected"))
        ws = self.company_id.get_connection(afip_ws).connect()
        if afip_ws == "wsbfe":
            ret = ws.GetParamNCM()
        else:
            raise UserError(_("Get NCM for ws %s is not implemented yet") % (afip_ws))
        msg = _("Zonas on AFIP\n%s\n. \nObservations: %s") % (
            "\n ".join(ret),
            ".\n".join([ws.Excepcion, ws.ErrMsg, ws.Obs]),
        )
        raise UserError(msg)

    def get_pyafipws_currencies(self):
        self.ensure_one()
        return self.env["res.currency"].get_pyafipws_currencies(
            afip_ws=self.afip_ws, company=self.company_id
        )

    def action_get_connection(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_("No AFIP WS selected"))
        self.company_id.get_connection(afip_ws).connect()

    def get_pyafipws_currency_rate(self, currency):
        raise UserError(
            currency.get_pyafipws_currency_rate(
                afip_ws=self.afip_ws,
                company=self.company_id,
            )[1]
        )
