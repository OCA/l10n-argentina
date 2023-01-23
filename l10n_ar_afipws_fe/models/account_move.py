##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
# from .pyi25 import PyI25
# import base64
# from io import BytesIO
import logging
import sys
import traceback

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# from datetime import datetime, date
_logger = logging.getLogger(__name__)

try:
    from pysimplesoap.client import SoapFault
except ImportError:
    _logger.debug("Can not `from pyafipws.soap import SoapFault`.")


class IrSequence(models.Model):
    _inherit = "ir.sequence"

    journal_id = fields.Many2one("account.journal", "Diario facturacion")


class AccountMove(models.Model):
    _inherit = "account.move"

    afip_mypyme_sca_adc = fields.Selection(
        selection=[
            ("SCA", "Sistema Circulacion Abierta"),
            ("ADC", "Agente Deposito Colectivo"),
        ],
        string="SCA o ADC",
        default="SCA",
    )
    afip_auth_verify_type = fields.Selection(
        related="company_id.afip_auth_verify_type",
    )
    document_number = fields.Char(copy=False, string="Document Number", readonly=True)
    afip_batch_number = fields.Integer(copy=False, string="Batch Number", readonly=True)
    afip_auth_verify_result = fields.Selection(
        [("A", "Aprobado"), ("O", "Observado"), ("R", "Rechazado")],
        string="AFIP authorization verification result",
        copy=False,
        readonly=True,
    )
    afip_auth_verify_observation = fields.Char(
        string="AFIP authorization verification observation",
        copy=False,
        readonly=True,
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
    # for compatibility
    afip_cae = fields.Char(
        related="afip_auth_code",
        readonly=False,
        string="CAE (only for backward compatibility)",
    )
    afip_cae_due = fields.Date(
        related="afip_auth_code_due",
        readonly=False,
        string="CAE due date (only for backward compatibility)",
    )

    afip_barcode = fields.Char(
        compute="_compute_barcode",
        string="AFIP Barcode",
        # store=True
    )
    l10n_ar_afip_barcode = fields.Char(
        compute="_compute_barcode",
        string="AFIP Barcode",
    )
    afip_barcode_img = fields.Binary(
        compute="_compute_barcode",
        string="AFIP Barcode Image",
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
    validation_type = fields.Char(
        "Validation Type", compute="_compute_validation_type", store=True
    )
    afip_fce_es_anulacion = fields.Boolean(
        string="FCE: Es anulacion?",
        help="""
        Solo utilizado en comprobantes MiPyMEs (FCE)
        del tipo débito o crédito. Debe informar:\n
        "- SI: sí el comprobante asociado (original) se
        encuentra rechazado por el comprador\n"
        "- NO: sí el comprobante asociado (original) NO se
        encuentra rechazado por el comprador
        """,
    )

    show_credit_button = fields.Boolean(
        "show_credit_button", compute="_compute_show_credit_button"
    )

    def _compute_show_credit_button(self):
        for rec in self:
            is_invoice = rec.move_type in ["in_invoice", "out_invoice"]
            is_posted = rec.state == "posted"
            is_not_paid_or_reversed = rec.payment_state not in ["paid", "reversed"]
            rec.show_credit_button = (
                is_invoice and is_posted and is_not_paid_or_reversed
            )

    @api.depends("journal_id", "afip_auth_code")
    def _compute_validation_type(self):
        for rec in self:
            if rec.journal_id.afip_ws and not rec.afip_auth_code:
                validation_type = self.env["res.company"]._get_environment_type()
                # if we are on homologation env and we dont have certificates
                # we validate only locally
                if validation_type == "homologation":
                    try:
                        rec.company_id.get_key_and_certificate(validation_type)
                    except Exception:
                        validation_type = False
                rec.validation_type = validation_type

    def get_related_invoices_data(self):
        """
        List related invoice information to fill CbtesAsoc.
        """
        self.ensure_one()
        # for now we only get related document for debit and credit notes
        # because, for eg, an invoice can not be related to an invocie and
        # that happens if you choose the modify option of the credit note
        # wizard. A mapping of which documents can be reported as related
        # documents would be a better solution
        if (
            self.l10n_latam_document_type_id.internal_type == "credit_note"
            and self.invoice_origin
        ):
            return self.search(
                [
                    ("commercial_partner_id", "=", self.commercial_partner_id.id),
                    ("company_id", "=", self.company_id.id),
                    ("document_number", "=", self.invoice_origin),
                    ("id", "!=", self.id),
                    (
                        "l10n_latam_document_type_id.l10n_ar_letter",
                        "=",
                        self.l10n_latam_document_type_id.l10n_ar_letter,
                    ),
                    (
                        "l10n_latam_document_type_id",
                        "!=",
                        self.l10n_latam_document_type_id.id,
                    ),
                    ("state", "not in", ["draft", "cancel"]),
                ],
                limit=1,
            )
        elif self.l10n_latam_document_type_id.internal_type == "debit_note":
            return self.debit_origin_id
        else:
            return self.browse()

    def action_post(self):
        """
        The last thing we do is request the cae because if an error occurs
        after cae requested, the invoice has been already validated on afip
        """
        res = super(AccountMove, self).action_post()
        self.check_afip_auth_verify_required()
        self.authorize_afip()
        return res

    # para cuando se crea, por ej, desde ventas o contratos
    @api.constrains("partner_id")
    # para cuando se crea manualmente la factura
    @api.onchange("partner_id")
    def _set_afip_journal(self):
        """
        Si es factura electrónica y es del exterior, buscamos diario
        para exportación
        TODO: implementar similar para elegir bono fiscal o factura con detalle
        """
        for rec in self.filtered(
            lambda x: (
                x.journal_id.l10n_ar_afip_pos_system == "RLI_RLM"
                and x.journal_id.type == "sale"
            )
        ):

            res_code = (
                rec.commercial_partner_id.l10n_ar_afip_responsibility_type_id.code
            )
            ws = rec.journal_id.afip_ws
            journal = self.env["account.journal"]
            domain = [
                ("company_id", "=", rec.company_id.id),
                ("point_of_sale_type", "=", "electronic"),
                ("type", "=", "sale"),
            ]
            # TODO mejorar que aca buscamos por codigo de resp mientras que
            # el mapeo de tipo de documentos es configurable por letras y,
            # por ejemplo, si se da letra e de RI a RI y se genera factura
            # para un RI queriendo forzar diario de expo, termina dando error
            # porque los ws y los res_code son incompatibles para esta logica.
            # El error lo da el metodo check_journal_document_type_journal
            # porque este metodo trata de poner otro diario sin actualizar
            # el tipo de documento
            if ws == "wsfe" and res_code in ["8", "9", "10"]:
                domain.append(("afip_ws", "=", "wsfex"))
                journal = journal.search(domain, limit=1)
            elif ws == "wsfex" and res_code not in ["8", "9", "10"]:
                domain.append(("afip_ws", "=", "wsfe"))
                journal = journal.search(domain, limit=1)

            if journal:
                rec.journal_id = journal.id

    def check_afip_auth_verify_required(self):
        verify_codes = [
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
            "11",
            "12",
            "13",
            "15",
            "19",
            "20",
            "21",
            "49",
            "51",
            "52",
            "53",
            "54",
            "60",
            "61",
            "63",
            "64",
        ]
        verification_required = self.filtered(
            lambda inv: inv.move_type in ["in_invoice", "in_refund"]
            and inv.afip_auth_verify_type == "required"
            and (inv.document_type_id and inv.document_type_id.code in verify_codes)
            and not inv.afip_auth_verify_result
        )
        if verification_required:
            raise UserError(
                _(
                    "You can not validate invoice as AFIP authorization "
                    "verification is required"
                )
            )

    def verify_on_afip(self):
        """
        cbte_modo = "CAE"                    # modalidad de emision: CAI, CAE,
        CAEA
        cuit_emisor = "20267565393"          # proveedor
        pto_vta = 4002                       # punto de venta habilitado en AFIP
        cbte_tipo = 1                        # 1: factura A (ver tabla de parametros)
        cbte_nro = 109                       # numero de factura
        cbte_fch = "20131227"                # fecha en formato aaaammdd
        imp_total = "121.0"                  # importe total
        cod_autorizacion = "63523178385550"  # numero de CAI, CAE o CAEA
        doc_tipo_receptor = 80               # CUIT (obligatorio Facturas A o M)
        doc_nro_receptor = "30628789661"     # numero de CUIT del cliente

        ok = wscdc.ConstatarComprobante(
            cbte_modo, cuit_emisor, pto_vta, cbte_tipo,
            cbte_nro, cbte_fch, imp_total, cod_autorizacion,
            doc_tipo_receptor, doc_nro_receptor)

        print "Resultado:", wscdc.Resultado
        print "Mensaje de Error:", wscdc.ErrMsg
        print "Observaciones:", wscdc.Obs
        """
        afip_ws = "wscdc"
        ws = self.company_id.get_connection(afip_ws).connect()
        for inv in self:
            cbte_modo = inv.afip_auth_mode
            cod_autorizacion = inv.afip_auth_code
            if not cbte_modo or not cod_autorizacion:
                raise UserError(_("AFIP authorization mode and Code are required!"))

            # get issuer and receptor depending on supplier or customer invoice
            if inv.type in ["in_invoice", "in_refund"]:
                issuer = inv.commercial_partner_id
                receptor = inv.company_id.partner_id
            else:
                issuer = inv.company_id.partner_id
                receptor = inv.commercial_partner_id

            cuit_emisor = issuer.cuit_required()

            receptor_doc_code = str(receptor.main_id_category_id.afip_code)
            doc_tipo_receptor = receptor_doc_code or "99"
            doc_nro_receptor = receptor_doc_code and receptor.main_id_number or "0"
            doc_type = inv.document_type_id
            if (
                doc_type.document_letter_id.name in ["A", "M"]
                and doc_tipo_receptor != "80"
                or not doc_nro_receptor
            ):
                raise UserError(
                    _(
                        "Para Comprobantes tipo A o tipo M:\n"
                        "*  el documento del receptor debe ser CUIT\n"
                        "*  el documento del Receptor es obligatorio\n"
                    )
                )

            cbte_nro = inv.invoice_number
            pto_vta = inv.journal_id.l10n_ar_afip_pos_number
            cbte_tipo = doc_type.code
            if not pto_vta or not cbte_nro or not cbte_tipo:
                raise UserError(
                    _(
                        "Point of sale and document number and document type "
                        "are required!"
                    )
                )
            cbte_fch = inv.invoice_date
            if not cbte_fch:
                raise UserError(_("Invoice Date is required!"))
            cbte_fch = cbte_fch.strftime("%Y%m%d")
            imp_total = str("%.2f" % inv.amount_total)

            _logger.info("Constatando Comprobante en afip")

            # atrapado de errores en afip
            msg = False
            try:
                ws.ConstatarComprobante(
                    cbte_modo,
                    cuit_emisor,
                    pto_vta,
                    cbte_tipo,
                    cbte_nro,
                    cbte_fch,
                    imp_total,
                    cod_autorizacion,
                    doc_tipo_receptor,
                    doc_nro_receptor,
                )
            except SoapFault as fault:
                msg = "Falla SOAP %s: %s" % (fault.faultcode, fault.faultstring)
            except Exception as e:
                msg = e
            except Exception:
                if ws.Excepcion:
                    # get the exception already parsed by the helper
                    msg = ws.Excepcion
                else:
                    # avoid encoding problem when raising error
                    msg = traceback.format_exception_only(sys.exc_type, sys.exc_value)[
                        0
                    ]
            if msg:
                raise UserError(_("AFIP Verification Error. %s" % msg))

            inv.write(
                {
                    "afip_auth_verify_result": ws.Resultado,
                    "afip_auth_verify_observation": "%s%s" % (ws.Obs, ws.ErrMsg),
                }
            )

    def _afip_auth_prechecks(self):
        # Ignore invoices with CAE saved
        if self.afip_auth_code:
            return False
        # Ignore invoice if pos_system not factura en linea
        if self.journal_id.l10n_ar_afip_pos_system not in ["RLI_RLM", "FEERCEL"]:
            return False
        # Check currency code set
        if not self.currency_id.l10n_ar_afip_code:
            raise ValidationError(_("No esta definido el codigo AFIP en la moneda"))
        return True

    def authorize_afip(self):
        for invoice in self:
            # Do checks before continuing with auth
            if not invoice._afip_auth_prechecks():
                continue

            afip_ws = invoice.journal_id.afip_ws
            # Raise error if invoice has no WS defined and is electronic
            if not afip_ws:
                raise UserError(
                    _(
                        "If you use electronic journals (invoice id %s) you need "
                        "configure AFIP WS on the journal"
                    )
                    % (invoice.id)
                )

            # -- AFIP Authorization: initialize -- #
            ws = invoice.company_id.get_connection(afip_ws).connect()
            if afip_ws == "wsfe":
                # Create objects invoice objects in ws
                header = invoice._build_afip_wsfe_header(afip_ws)
                vat_taxes = invoice._build_afip_wsfe_vat_taxes(afip_ws)
                other_taxes = invoice._build_afip_wsfe_other_taxes(afip_ws)
                cbte_asoc = invoice._build_afip_wsfe_cbte_asoc(afip_ws)
                # Assign next invoice number
                pos_number = self.journal_id.l10n_ar_afip_pos_number
                cbte_nro = invoice._get_afip_next_invoice_number()
                header["cbt_desde"] = header["cbt_hasta"] = header[
                    "cbte_nro"
                ] = cbte_nro
                # Crate webservice objects
                ws.CrearFactura(**header)
                for vat_tax in vat_taxes:
                    ws.AgregarIva(**vat_tax)
                for other_tax in other_taxes:
                    ws.AgregarTributo(**other_tax)
                for cbte in cbte_asoc:
                    _logger.info(
                        "AFIP Authorization: Adding asociated document - %s" % str(cbte)
                    )
                    ws.AgregarCmpAsoc(**cbte)

            # -- AFIP Authorization: Authorize -- #
            error_msg = False
            try:
                if afip_ws == "wsfe":
                    ws.CAESolicitar()
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
                    _("AFIP Validation Error. %s" % error_msg)
                    + " XML Request: %s XML Response: %s"
                    % (ws.XmlRequest, ws.XmlResponse)
                )
                raise UserError(_("AFIP Validation Error. %s" % error_msg))
            msg = "\n".join([ws.Obs or "", ws.ErrMsg or ""])
            if not ws.CAE or ws.Resultado != "A":
                _logger.warning("AFIP Validation Error. Error en la obtencion del CAE.")
                raise UserError(_("AFIP Validation Error. %s" % msg))
            _logger.info(
                "CAE solicitado con exito. CAE: %s. Resultado %s"
                % (ws.CAE, ws.Resultado)
            )

            # -- AFIP Authorization: AFIP Result -- #
            cae_vto = afip_ws == "wsfex" and ws.FchVencCAE or ws.Vencimiento
            cae_vto = cae_vto[:4] + "-" + cae_vto[4:6] + "-" + cae_vto[6:8]
            invoice.write(
                {
                    "afip_auth_mode": "CAE",
                    "afip_auth_code": ws.CAE,
                    "afip_auth_code_due": cae_vto,
                    "afip_result": ws.Resultado,
                    "afip_message": "\n".join([ws.Obs or "", ws.ErrMsg or ""]),
                    "afip_xml_request": ws.XmlRequest,
                    "afip_xml_response": ws.XmlResponse,
                    "document_number": str(pos_number).zfill(5)
                    + "-"
                    + str(cbte_nro).zfill(8),
                    "name": self.l10n_latam_document_type_id.doc_code_prefix
                    + " "
                    + str(pos_number).zfill(5)
                    + "-"
                    + str(cbte_nro).zfill(8),
                }
            )
            invoice._cr.commit()

    def _build_afip_wsfe_header(self, afip_ws):
        partner = self.commercial_partner_id
        journal = self.journal_id
        pos_number = journal.l10n_ar_afip_pos_number
        doc_afip_code = self.l10n_latam_document_type_id.code
        invoice_letter = self.l10n_latam_document_type_id.l10n_ar_letter

        header = {
            "concepto": int(self.l10n_ar_afip_concept) or 1,
            "tipo_doc": partner.l10n_latam_identification_type_id.l10n_ar_afip_code
            or 99,
            "nro_doc": partner.vat,
            "tipo_cbte": doc_afip_code,
            "punto_vta": pos_number,
            "cbte_nro": None,
            "cbt_desde": None,
            "cbt_hasta": None,
            "fecha_cbte": self.invoice_date.strftime("%Y%m%d"),
            "fecha_serv_desde": None,
            "fecha_serv_hasta": None,
            "fecha_venc_pago": None,
            "imp_total": 0,
            "imp_tot_conc": str("%.2f" % self.vat_untaxed_base_amount),
            "imp_neto": invoice_letter == "C"
            and str("%.2f" % self.amount_untaxed)
            or str("%.2f" % self.vat_taxable_amount),
            "imp_iva": str("%.2f" % self.vat_amount),
            "imp_trib": str("%.2f" % self.other_taxes_amount),
            "imp_op_ex": str("%.2f" % self.vat_exempt_base_amount),
            "moneda_id": self.currency_id.l10n_ar_afip_code or "PES",
            "moneda_ctz": round(1 / self.currency_id.rate, 2) or 1.000,
        }
        # assign amount_total
        amount_total = self.amount_untaxed
        for move_tax in self.move_tax_ids:
            amount_total += move_tax.tax_amount
        header["imp_total"] = amount_total

        # Si el concepto no es "1", se debe indicar fecha de servicios
        if int(header["concepto"]) != 1:
            header["fecha_serv_desde"] = self.l10n_ar_afip_service_start.strftime(
                "%Y%m%d"
            )
            header["fecha_serv_hasta"] = self.l10n_ar_afip_service_end.strftime(
                "%Y%m%d"
            )

        # Webserice: Facturacion - Caso Facturas Mipyme
        mipyme_fce = int(doc_afip_code) in [201, 206, 211]
        other_fce = int(doc_afip_code) not in [202, 203, 207, 208, 212, 213]
        if int(header["concepto"]) != 1 and other_fce or mipyme_fce:
            header["fecha_venc_pago"] = self.invoice_date_due or self.invoice_date
        return header

    def _build_afip_wsfe_vat_taxes(self, afip_ws):
        vat_taxes = []
        for move_tax in self.move_tax_ids:
            if (
                move_tax.tax_id.tax_group_id.tax_type == "vat"
                and move_tax.tax_id.tax_group_id.l10n_ar_vat_afip_code != "2"
            ):
                vat_taxes.append(
                    {
                        "iva_id": move_tax.tax_id.tax_group_id.l10n_ar_vat_afip_code,
                        "base_imp": "%.2f" % move_tax.base_amount,
                        "importe": "%.2f" % move_tax.tax_amount,
                    }
                )
        return vat_taxes

    def _build_afip_wsfe_cbte_asoc(self, afip_ws):
        cbte_asocs = []
        for cbte in self.get_related_invoices_data():
            cbte_asocs.append(
                {
                    "tipo": cbte.l10n_latam_document_type_id.code,
                    "pto_vta": cbte.journal_id.l10n_ar_afip_pos_number,
                    "nro": int(cbte.document_number.split("-")[1]),
                    "cuit": self.company_id.vat,
                    "fecha": str(cbte.invoice_date).replace("-", ""),
                }
            )
        return cbte_asocs

    def _build_afip_wsfe_other_taxes(self, afip_ws):
        other_taxes = []
        for move_tax in self.move_tax_ids:
            if move_tax.tax_id.tax_group_id.tax_type != "vat":
                other_taxes.append(
                    {
                        "tributo_id": move_tax.tax_id.tax_group_id.l10n_ar_tribute_afip_code,
                        "base_imp": str("%.2f" % move_tax.base_amount),
                        "importe": str("%.2f" % move_tax.tax_amount),
                        "alic": None,
                    }
                )
        return other_taxes

    def _get_afip_next_invoice_number(self):
        return (
            int(
                self.l10n_latam_document_type_id.get_pyafipws_last_invoice(self)[
                    "result"
                ]
            )
            + 1
        )
