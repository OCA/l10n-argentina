# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountJournalWs(models.Model):
    _inherit = "account.journal"  # pylint: disable=consider-merging-classes-inherited

    def test_pyafipws_dummy(self):
        """
        AFIP Description: Método Dummy para verificación de funcionamiento de
        infraestructura (FEDummy)
        """
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_("No AFIP WS selected"))
        ws = self.company_id.get_connection(afip_ws).connect()
        ws.Dummy()
        title = _("AFIP service %s\n") % afip_ws
        if ws.AppServerStatus == ws.DbServerStatus == ws.AuthServerStatus == "OK":
            notification_type = "success"
        else:
            notification_type = "warning"
        msg = (
            'AppServerStatus: "%(appserver_status)s"\n'
            'DbServerStatus: "%(dbserver_status)s"\n'
            'AuthServerStatus: "%(authserver_status)s"\n'
            % {
                "appserver_status": ws.AppServerStatus,
                "dbserver_status": ws.DbServerStatus,
                "authserver_status": ws.AuthServerStatus,
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": msg,
                "type": notification_type,
                "sticky": True,  # True/False will display for few seconds if false
            },
        }

    def test_pyafipws_point_of_sales(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_("No AFIP WS selected"))
        ws = self.company_id.get_connection(afip_ws).connect()
        if hasattr(self, "%s_pyafipws_point_of_sales" % afip_ws):
            ret = getattr(self, "%s_pyafipws_point_of_sales" % afip_ws)(ws)
        else:
            raise UserError(
                _("Get point of sale for ws %s is not implemented yet") % (afip_ws)
            )
        msg = _(' "%(ret)s" "%(exeptions)s"') % {
            "ret": ". ".join(ret),
            "exeptions": " - ".join([ws.Excepcion, ws.ErrMsg, ws.Obs]),
        }
        title = _("Enabled Point Of Sales on AFIP\n")
        raise UserError(title + msg)

    def get_pyafipws_post_invoice_numbers(self):
        for journal_id in self:
            msg = []
            afip_ws = journal_id.afip_ws
            if not afip_ws:
                raise UserError(
                    _("No AFIP WS selected on point of sale %s") % (journal_id.name)
                )
            ws = journal_id.company_id.get_connection(afip_ws).connect()
            ret = getattr(self, "%s_pyafipws_cuit_document_classes" % afip_ws)(ws)

            for document_line in ret:
                document_type = document_line.split(",")
                # call the webservice method to get the last invoice at AFIP:
                if hasattr(self, "%s_get_pyafipws_last_invoice" % afip_ws):
                    obj_document_type = type(
                        "obj", (object,), {"code": document_type[0]}
                    )

                    document_type.append(
                        getattr(self, "%s_get_pyafipws_last_invoice" % afip_ws)(
                            journal_id.l10n_ar_afip_pos_number, obj_document_type, ws
                        )
                    )
                else:
                    raise UserError(_("AFIP WS %s not implemented") % afip_ws)
                msg.append(
                    "%s %05d-%08d"
                    % (document_type[1], int(document_type[0]), int(document_type[-1]))
                )
            journal_id.message_post(body="<br/>\n".join(msg))

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
            else:
                return _("AFIP WS %s not implemented") % afip_ws
            return last

        except ValueError as error:
            _logger.warning("exception in get_pyafipws_last_invoice: %s" % (str(error)))
            if "The read operation timed out" in str(error):
                raise UserError(
                    _("Servicio AFIP Ocupado reintente en unos minutos")
                ) from error
            else:
                raise UserError(
                    _(
                        "Hubo un error al conectarse a AFIP, contacte a su"
                        " proveedor de Odoo para mas información"
                    )
                ) from error

    def get_pyafipws_currency_rate(self, currency):
        raise UserError(
            currency.get_pyafipws_currency_rate(
                afip_ws=self.afip_ws,
                company=self.company_id,
            )[1]
        )

    def get_pyafipws_cuit_document_classes(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_("No AFIP WS selected"))
        ws = self.company_id.get_connection(afip_ws).connect()
        if hasattr(self, "%s_pyafipws_cuit_document_classes" % afip_ws):
            ret = getattr(self, "%s_pyafipws_cuit_document_classes" % afip_ws)(ws)
        else:
            raise UserError(
                _("Get document types for ws %s is not implemented yet") % (afip_ws)
            )
        msg = _(
            'Authorized Document Clases on AFIP"\n%(ret)s"\n \nObservations: "%(exeptions)s"'
        ) % {
            "ret": ". ".join(ret),
            "exeptions": " - ".join([ws.Excepcion, ws.ErrMsg, ws.Obs]),
        }
        raise UserError(msg)

    def get_pyafipws_zonas(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_("No AFIP WS selected"))
        ws = self.company_id.get_connection(afip_ws).connect()
        if hasattr(self, "%s_pyafipws_zonas" % afip_ws):
            ret = getattr(self, "%s_pyafipws_zonas" % afip_ws)(ws)

        else:
            raise UserError(_("Get zonas for ws %s is not implemented yet") % (afip_ws))
        msg = _('Zonas on AFIP\n%(ret)s"\n \nObservations: "%(exeptions)s"') % {
            "ret": ". ".join(ret),
            "exeptions": " - ".join([ws.Excepcion, ws.ErrMsg, ws.Obs]),
        }
        raise UserError(msg)

    def get_pyafipws_NCM(self):
        self.ensure_one()
        afip_ws = self.afip_ws
        if not afip_ws:
            raise UserError(_("No AFIP WS selected"))
        ws = self.company_id.get_connection(afip_ws).connect()
        if hasattr(self, "%s_pyafipws_NCM" % afip_ws):
            ret = getattr(self, "%s_pyafipws_NCM" % afip_ws)(ws)
        else:
            raise UserError(_("Get NCM for ws %s is not implemented yet") % (afip_ws))
        msg = _('NCM on AFIP\n%(ret)s"\n \nObservations: "%(exeptions)s"') % {
            "ret": ". ".join(ret),
            "exeptions": " - ".join([ws.Excepcion, ws.ErrMsg, ws.Obs]),
        }
        raise UserError(msg)

    def wsbfe_pyafipws_NCM(self, ws):
        return ws.GetParamNCM()

    def wsbfe_pyafipws_zonas(self, ws):
        return ws.GetParamZonas()

    def wsfex_pyafipws_cuit_document_classes(self, ws):
        return ws.GetParamTipoCbte(sep=",")

    def wsfe_pyafipws_cuit_document_classes(self, ws):
        return ws.ParamGetTiposCbte(sep=",")

    def wsbfe_pyafipws_cuit_document_classes(self, ws):
        return ws.GetParamTipoCbte()

    def wsfex_pyafipws_point_of_sales(self, ws):
        return ws.GetParamPtosVenta()

    def wsfe_pyafipws_point_of_sales(self, ws):
        return ws.ParamGetPtosVenta(sep=" ")

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
