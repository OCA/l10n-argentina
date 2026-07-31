# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
import json
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round

_logger = logging.getLogger(__name__)

# `Resultado` values ARCA returns. Kept as a constant (instead of a literal in
# the field definition) because the failure logger validates against it before
# writing: an unexpected response must not bring the posting down.
L10N_AR_ARCA_RESULT_SELECTION = [("A", "Aprobado"), ("R", "Rechazado")]
L10N_AR_ARCA_RESULT_VALUES = frozenset(
    value for value, _label in L10N_AR_ARCA_RESULT_SELECTION
)


class L10nArArcaRejection(UserError):
    """ARCA answered, and the answer was a rejection.

    Exists to tell "ARCA said no" (a business answer, carrying a code and
    remarks worth storing on the document) apart from "I could not reach ARCA"
    (network, certificate, library). Both leave the invoice posted without a
    CAE, but only the first one has a verdict to record.
    """

    def __init__(self, message, resultado=None, observations=None):
        super().__init__(message)
        self.resultado = resultado
        self.observations = observations


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ar_arca_edi_enabled = fields.Boolean(
        related="journal_id.l10n_ar_arca_edi_enabled",
        help="Only used to control the visibility of the 'Solicitar CAE' button "
        "in the view: without it the button shows up on any posted invoice, even "
        "from a journal with no electronic point of sale.",
    )
    l10n_ar_arca_cae = fields.Char(string="CAE", copy=False)
    l10n_ar_arca_cae_due_date = fields.Date(string="CAE due date", copy=False)
    l10n_ar_arca_result = fields.Selection(
        selection=L10N_AR_ARCA_RESULT_SELECTION,
        string="ARCA Result",
        copy=False,
        help="ARCA never returns a third Resultado value on its own: "
        "'Observado' is the combination of Resultado=A with Observaciones filled "
        "in (approval with remarks), not a separate code.",
    )
    l10n_ar_arca_observations = fields.Text(
        string="ARCA Remarks",
        copy=False,
        help="Remarks returned by ARCA even on an approval (Resultado=A with "
        "Observaciones is not an error, it is an approval with remarks).",
    )

    def _post(self, soft=True):
        posted = super()._post(soft=soft)

        to_authorize = posted.filtered(
            lambda m: (
                m.journal_id.l10n_ar_arca_edi_enabled
                and m.move_type in ("out_invoice", "out_refund")
                and not m.l10n_ar_arca_cae
            )
        )
        for move in to_authorize:
            # Every invoice is authorized independently, with its own
            # try/except: a rejection does NOT undo the posting nor the number
            # already assigned by the super()._post() above. The number is
            # consumed before we know ARCA's verdict because Odoo numbers the
            # document inside `_post()` itself; numbering only afterwards would
            # require peeking at the next number without consuming it, which is
            # fragile under concurrency. Numbering and authorization are not
            # atomic in Argentine electronic invoicing, and a number gap caused
            # by a rejection is an accepted reality, not a design flaw. The
            # invoice stays posted WITHOUT a CAE and has to be resent (manual
            # button in this version; a cron for pending documents is a ROADMAP
            # item, not implemented yet).
            try:
                # `savepoint()` is mandatory: without it a database error
                # inside the authorization leaves the cursor aborted and
                # EVERYTHING after it fails, including the notice to the user
                # and the authorization of the other invoices in the batch.
                # With the savepoint only this invoice's work is rolled back
                # and the posting stands.
                with self.env.cr.savepoint():
                    move._l10n_ar_arca_request_cae()
            except Exception as error:
                _logger.exception(
                    "Could not request the CAE for %s. The invoice stays "
                    "posted without a CAE; use 'Solicitar CAE' to try again.",
                    move.display_name,
                )
                move._l10n_ar_arca_log_cae_failure(error)
        return posted

    def _l10n_ar_arca_log_cae_failure(self, error):
        """Make the authorization failure visible to whoever posted the invoice.

        The server log does not do the job: the person confirming the invoice
        does not read it, and with no sign in the interface the invoice gets
        printed and handed over without a CAE and without a QR code, the
        problem only surfacing when the customer or the tax authority refuses
        it. The chatter is the right channel because it follows the document
        and stays in its history, and the message is written after the
        savepoint has rolled back whatever the attempt wrote.

        Logging the failure must never be the reason the posting breaks: hence
        it runs in a savepoint of its own and swallows its own exception. The
        concrete case behind that defence is ARCA returning a `Resultado`
        outside the field domain, which would make `write()` raise a
        `ValueError` and bring down exactly the confirmation we were trying to
        preserve.
        """
        self.ensure_one()
        detail = str(error) or error.__class__.__name__
        resultado = getattr(error, "resultado", None)
        if resultado not in L10N_AR_ARCA_RESULT_VALUES:
            resultado = False
        observations = getattr(error, "observations", None)
        if not isinstance(observations, str) or not observations:
            observations = detail

        try:
            with self.env.cr.savepoint():
                self.write(
                    {
                        "l10n_ar_arca_result": resultado,
                        "l10n_ar_arca_observations": observations,
                    }
                )
                self.message_post(
                    body=_(
                        "Could not obtain the CAE from ARCA: %(detail)s\n\n"
                        "The invoice is posted and numbered, but WITHOUT a CAE: "
                        "it is not a valid document yet. Use the 'Solicitar CAE' "
                        "button to try again.",
                        detail=detail,
                    )
                )
        except Exception:
            _logger.exception(
                "Could not record the ARCA authorization error on document "
                "%s. The original error was: %s",
                self.display_name,
                detail,
            )

    def action_l10n_ar_arca_request_cae(self):
        """Manual button: (re)tries the authorization of an invoice with no CAE."""
        for move in self:
            move._l10n_ar_arca_request_cae()

    def _l10n_ar_arca_webservice(self):
        """Key of the ARCA webservice that authorizes this document.

        Routing extension point. A module serving another webservice (WSFEXv1
        for exports, WSBFEv1 for bono fiscal) overrides this method returning
        its own key when it recognizes the document, and implements
        `_l10n_ar_arca_request_cae_<key>`. Calling `super()` for the cases that
        are not its own keeps the chain working with as many webservices as
        there happen to be.

        The alternative this design avoids is routing with `filtered()` plus
        `super()` over a subset: it works with two webservices and becomes a
        fragile chain of partial overrides from the third one onwards.
        """
        self.ensure_one()
        return "wsfev1"

    def _l10n_ar_arca_request_cae(self):
        """Common preconditions and dispatch to the document webservice."""
        self.ensure_one()
        if self.l10n_ar_arca_cae:
            raise UserError(_("This invoice already has a CAE."))
        if self.state != "posted":
            raise UserError(_("The CAE can only be requested for a posted invoice."))

        webservice = self._l10n_ar_arca_webservice()
        handler = getattr(self, f"_l10n_ar_arca_request_cae_{webservice}", None)
        if handler is None:
            raise UserError(
                _(
                    "There is no installed module able to request the CAE "
                    "through the ARCA %(webservice)s webservice for document "
                    "%(document)s."
                )
                % {"webservice": webservice, "document": self.display_name}
            )
        return handler()

    def _l10n_ar_arca_request_cae_wsfev1(self):
        """Domestic market electronic invoice (WSFEv1)."""
        self.ensure_one()
        transmissao = self.company_id._l10n_ar_arca_get_transmissao("TransmissaoWSFEv1")
        fe_request = self._l10n_ar_arca_build_fecae_request()
        response = transmissao.fecae_solicitar(fe_request)
        self._l10n_ar_arca_process_fecae_response(response)

    def _l10n_ar_arca_build_fecae_request(self):
        """Build the arcalib `Fecaerequest` from the amounts the core already
        computed (`_get_vat`, `_l10n_ar_get_amounts`).

        No new tax rule lives here, only field remapping: the tax engine of the
        core is the single source of truth for the amounts.
        """
        self.ensure_one()
        from arcalib.wsfev1.bindings.wsfev1 import (
            AlicIva,
            ArrayOfAlicIva,
            ArrayOfFecaedetRequest,
            FecaecabRequest,
            FecaedetRequest,
            Fecaerequest,
        )

        journal = self.journal_id
        doc_type = self.l10n_latam_document_type_id
        partner = self.partner_id

        # `base_lines` passed explicitly (not the implicit default of
        # `_l10n_ar_get_amounts`): the core returns all zeros when called
        # without the argument.
        base_lines, _tax_lines = self._get_rounded_base_and_tax_lines()
        amounts = self._l10n_ar_get_amounts(base_lines)
        vat_lines = self._get_vat(base_lines)

        iva = None
        if vat_lines:
            iva = ArrayOfAlicIva(
                AlicIva=[
                    AlicIva(
                        Id=int(line["Id"]),
                        BaseImp=line["BaseImp"],
                        Importe=line["Importe"],
                    )
                    for line in vat_lines
                ]
            )

        doc_number_parts = self._l10n_ar_get_document_number_parts(
            self.l10n_latam_document_number, doc_type.code
        )
        invoice_number = doc_number_parts["invoice_number"]

        service_start, service_end = self._l10n_ar_arca_service_dates()
        payment_due_date = self._l10n_ar_arca_payment_due_date()

        det = FecaedetRequest(
            Concepto=int(self.l10n_ar_afip_concept or "1"),
            DocTipo=int(
                partner.l10n_latam_identification_type_id.l10n_ar_afip_code or "99"
            ),
            DocNro=partner._get_id_number_sanitize(),
            CbteDesde=invoice_number,
            CbteHasta=invoice_number,
            CbteFch=self.invoice_date.strftime("%Y%m%d"),
            ImpTotal=self._l10n_ar_arca_imp_total(amounts),
            ImpTotConc=amounts["vat_untaxed_base_amount"],
            ImpNeto=amounts["vat_taxable_amount"],
            ImpOpEx=amounts["vat_exempt_base_amount"],
            ImpTrib=amounts["not_vat_taxes_amount"],
            ImpIVA=amounts["vat_amount"],
            FchServDesde=service_start.strftime("%Y%m%d") if service_start else None,
            FchServHasta=service_end.strftime("%Y%m%d") if service_end else None,
            FchVtoPago=payment_due_date.strftime("%Y%m%d")
            if payment_due_date
            else None,
            MonId=self.currency_id.l10n_ar_afip_code or "PES",
            MonCotiz=self._l10n_ar_arca_currency_rate(),
            CondicionIVAReceptorId=int(
                partner.l10n_ar_afip_responsibility_type_id.code
                or self.env.ref("l10n_ar.res_CF").code
            ),
            CbtesAsoc=self._l10n_ar_arca_build_cbtes_asoc(),
            Tributos=self._l10n_ar_arca_build_tributos(base_lines),
            Iva=iva,
        )

        return Fecaerequest(
            FeCabReq=FecaecabRequest(
                CantReg=1,
                PtoVta=journal.l10n_ar_afip_pos_number,
                CbteTipo=int(doc_type.code),
            ),
            FeDetReq=ArrayOfFecaedetRequest(FECAEDetRequest=[det]),
        )

    # ARCA concepts that involve rendering a service and therefore require the
    # period to be reported (FchServDesde/FchServHasta). The list comes from the
    # Odoo core itself (LGPL-3): `l10n_ar/models/account_move.py`,
    # `_set_afip_service_dates`, which only fills those dates when
    # `l10n_ar_afip_concept in ['2', '3', '4']` (2 = Servicios,
    # 3 = Productos y Servicios, 4 = Otros). The same explicit list is used
    # here, rather than "anything that is not 1", so that no dates are sent if
    # ARCA ever adds a concept that is not about services.
    L10N_AR_ARCA_CONCEPTS_WITH_SERVICE_DATES = ("2", "3", "4")

    def _l10n_ar_arca_service_dates(self):
        """Service period to report on the document, or (False, False) when the
        concept does not require it.

        The core already guarantees the dates are filled on posting
        (`_set_afip_service_dates`), so the only decision here is whether they
        belong in the payload.
        """
        self.ensure_one()
        if self.l10n_ar_afip_concept in self.L10N_AR_ARCA_CONCEPTS_WITH_SERVICE_DATES:
            return self.l10n_ar_afip_service_start, self.l10n_ar_afip_service_end
        return False, False

    # Concepts that make the payment due date mandatory (`FchVtoPago` of
    # WSFEv1): 2 = Servicios and 3 = Productos y Servicios. Unlike the service
    # dates, concept 4 (Otros) is not included: the obligation is tied to
    # rendering a service.
    L10N_AR_ARCA_CONCEPTS_WITH_PAYMENT_DUE_DATE = ("2", "3")

    def _l10n_ar_arca_payment_due_date(self):
        """Payment due date to report, or False when not required.

        ARCA requires the field on service invoices. Odoo already derives the
        date from the payment term (`invoice_date_due`); with no payment term
        the core leaves it equal to the invoice date, which is the right value
        to report for an immediate payment.
        """
        self.ensure_one()
        if (
            self.l10n_ar_afip_concept
            not in self.L10N_AR_ARCA_CONCEPTS_WITH_PAYMENT_DUE_DATE
        ):
            return False
        return self.invoice_date_due or self.invoice_date

    def _l10n_ar_arca_amount_sign(self):
        """Sign to apply to the document amounts: -1 or 1.

        Some document types serve as invoice AND as credit note. For those the
        core flips the sign of every amount when the document is a reversal, so
        ARCA can tell one from the other. The rule is read from the core itself
        (`l10n_ar._l10n_ar_get_amounts`) rather than duplicated as a literal
        list, so it cannot drift if Odoo SA changes the codes.
        """
        self.ensure_one()
        if self.move_type in (
            "out_refund",
            "in_refund",
        ) and self.l10n_latam_document_type_id.code in (
            self._get_l10n_ar_codes_used_for_inv_and_ref()
        ):
            return -1
        return 1

    def _l10n_ar_arca_imp_total(self, amounts):
        """`ImpTotal` of the document, summed from its own parts.

        ARCA validates `ImpTotal = ImpTotConc + ImpNeto + ImpOpEx + ImpTrib +
        ImpIVA`. Summing the parts instead of sending `amount_total` makes that
        identity hold by construction and, as a bonus, inherits the sign the
        core applied to the parts: `amount_total` is always positive, even on a
        credit note whose code requires negative amounts, and that sign
        mismatch used to be rejected by ARCA.
        """
        self.ensure_one()
        return float_round(
            amounts["vat_untaxed_base_amount"]
            + amounts["vat_taxable_amount"]
            + amounts["vat_exempt_base_amount"]
            + amounts["not_vat_taxes_amount"]
            + amounts["vat_amount"],
            precision_digits=2,
        )

    # Core fields pointing at the source document. `reversed_entry_id`
    # (reversal/credit note) comes from `account`; `debit_origin_id` only exists
    # when `account_debit_note` is installed, hence the check against `_fields`.
    L10N_AR_ARCA_ORIGIN_FIELDS = ("reversed_entry_id", "debit_origin_id")

    def _l10n_ar_arca_find_related_invoice(self):
        """Source document of this comprobante, for `CbtesAsoc`.

        Instead of deciding by document type, this looks at the link Odoo
        itself recorded: if the invoice was created by reversing or debiting
        another one, the matching field is set. That covers for free any
        document type ARCA may come to treat as associated, and does not depend
        on keeping a list of `internal_type` up to date.
        """
        self.ensure_one()
        for field_name in self.L10N_AR_ARCA_ORIGIN_FIELDS:
            if field_name not in self._fields:
                continue
            origin = self[field_name]
            if origin:
                return origin
        return self.browse()

    def _l10n_ar_arca_build_cbtes_asoc(self):
        self.ensure_one()
        from arcalib.wsfev1.bindings.wsfev1 import ArrayOfCbteAsoc, CbteAsoc

        related = self._l10n_ar_arca_find_related_invoice()
        if not related:
            return None
        parts = related._l10n_ar_get_document_number_parts(
            related.l10n_latam_document_number,
            related.l10n_latam_document_type_id.code,
        )
        return ArrayOfCbteAsoc(
            CbteAsoc=[
                CbteAsoc(
                    Tipo=int(related.l10n_latam_document_type_id.code),
                    PtoVta=parts["point_of_sale"],
                    Nro=parts["invoice_number"],
                )
            ]
        )

    def _l10n_ar_arca_build_tributos(self, base_lines=None):
        """`Tributos` array of WSFEv1: one entry per tax group carrying an ARCA
        tribute code (IIBB perception, municipal, internal taxes, other
        perceptions, everything aggregated into `not_vat_taxes_amount` that is
        neither VAT nor Ganancias).

        Grouped by `tax_group_id` rather than by line, so the same tribute is
        not repeated in several entries when the invoice has more than one line
        with the same tax.
        """
        self.ensure_one()
        from arcalib.wsfev1.bindings.wsfev1 import ArrayOfTributo, Tributo

        if base_lines is None:
            base_lines, _tax_lines = self._get_rounded_base_and_tax_lines()

        # Aggregation delegated to the core tax engine (LGPL-3), the same one
        # `l10n_ar._l10n_ar_get_amounts` uses to reach `not_vat_taxes_amount`:
        # `_aggregate_base_lines_tax_details` takes a grouping function and
        # returns base and tax already summed per key. That keeps the
        # `Tributos` array consistent by construction with the `ImpTrib` of the
        # header (ARCA cross-checks the two) without reimplementing any tax
        # rule here.
        AccountTax = self.env["account.tax"]

        def group_by_tribute(_base_line, tax_data):
            """Key is the tax group, only for tributes with an ARCA code."""
            if not tax_data:
                return None
            tax_group = tax_data["tax"].tax_group_id
            if not tax_group.l10n_ar_tribute_afip_code:
                return None
            return tax_group

        aggregated = AccountTax._aggregate_base_lines_aggregated_values(
            AccountTax._aggregate_base_lines_tax_details(base_lines, group_by_tribute)
        )

        # Same sign the core applied to the header parts: ARCA cross-checks
        # the sum of this array against `ImpTrib`, and using absolute values
        # here diverged from the signed header on a credit note.
        sign = self._l10n_ar_arca_amount_sign()

        tributos = []
        for tax_group, values in aggregated.items():
            if not tax_group:
                continue
            tributos.append(
                Tributo(
                    Id=int(tax_group.l10n_ar_tribute_afip_code),
                    Desc=tax_group.name,
                    BaseImp=sign * values["base_amount_currency"],
                    # Alic=0: the effective amount already travels in
                    # `Importe`, and the rate of a non-VAT tribute may be
                    # fixed, tiered or set per partner (IIBB perception), so
                    # there is not always a single rate describing the entry.
                    # Unlike the `Iva` array, where the rate is the grouping
                    # key itself.
                    Alic=0.0,
                    Importe=sign * values["tax_amount_currency"],
                )
            )
        if not tributos:
            return None
        return ArrayOfTributo(Tributo=tributos)

    def _l10n_ar_arca_currency_rate(self):
        self.ensure_one()
        # MonCotiz=1 when the document currency already is the company
        # currency (the common case, ARS/ARS).
        #
        # Conversion: `invoice_currency_rate` in Odoo is "how many units of the
        # document currency are worth 1 unit of the company currency" (core
        # `account`: "Currency rate from company currency to document
        # currency"). ARCA asks for the opposite, how many pesos 1 unit of the
        # foreign currency is worth, hence the inverse. Check it with an
        # example: 1 ARS = 0.001 USD -> invoice_currency_rate = 0.001 and
        # MonCotiz must be 1000 (1 USD = 1000 ARS).
        #
        # Fetching the foreign currency rate from WSFEv1 itself
        # (FEParamGetCotizacion) is out of scope here: see readme/ROADMAP.rst.
        if self.currency_id == self.company_id.currency_id:
            return 1.0
        return 1 / (self.invoice_currency_rate or 1.0)

    def _l10n_ar_arca_process_fecae_response(self, response):
        self.ensure_one()
        result = response.FECAESolicitarResult
        if not result or not result.FeDetResp or not result.FeDetResp.FECAEDetResponse:
            raise UserError(_("Unexpected response from ARCA: no FeDetResp."))

        det = result.FeDetResp.FECAEDetResponse[0]
        # Resultado/Observaciones come from FEDetResponse, the base class that
        # FECAEDetResponse (FecaedetResponse in the binding) extends in the XSD.
        # They do not show up in the generated class body, only through Python
        # inheritance (dataclasses.fields() confirms it).
        observations = None
        if det.Observaciones and det.Observaciones.Obs:
            observations = "; ".join(
                f"[{obs.Code}] {obs.Msg}" for obs in det.Observaciones.Obs
            )

        if det.Resultado != "A":
            # Nothing is written before raising: `_post` wraps the
            # authorization in a savepoint, so any write done here would be
            # rolled back. The verdict is persisted by
            # `_l10n_ar_arca_log_cae_failure`, from the data the exception
            # carries.
            raise L10nArArcaRejection(
                _("ARCA rejected the CAE request (%(resultado)s): %(obs)s")
                % {
                    "resultado": det.Resultado,
                    "obs": observations or _("no detail"),
                },
                resultado=det.Resultado,
                observations=observations,
            )

        self.write(
            {
                "l10n_ar_arca_cae": det.CAE,
                "l10n_ar_arca_cae_due_date": fields.Date.from_string(
                    f"{det.CAEFchVto[:4]}-{det.CAEFchVto[4:6]}-{det.CAEFchVto[6:8]}"
                ),
                "l10n_ar_arca_result": det.Resultado,
                "l10n_ar_arca_observations": observations,
            }
        )

    def _l10n_ar_arca_qr_data(self):
        """Payload of the QR code required on electronic invoices (RG 4892/2020).

        Fields and format follow the public ARCA specification "Código QR -
        Especificación Técnica"
        (https://www.afip.gob.ar/fe/qr/especificaciones.asp).
        Still TO BE VERIFIED against the official document and against a real
        QR accepted in homologación before considering it final: see
        readme/ROADMAP.rst.
        """
        self.ensure_one()
        doc_type = self.l10n_latam_document_type_id
        partner = self.partner_id
        parts = self._l10n_ar_get_document_number_parts(
            self.l10n_latam_document_number, doc_type.code
        )
        base_lines, _tax_lines = self._get_rounded_base_and_tax_lines()
        return {
            "ver": 1,
            "fecha": self.invoice_date.strftime("%Y-%m-%d"),
            "cuit": self.company_id.partner_id._get_id_number_sanitize(),
            "ptoVta": parts["point_of_sale"],
            "tipoCmp": int(doc_type.code),
            "nroCmp": parts["invoice_number"],
            # Same total as the CAE payload (and same sign): the QR has to
            # match the authorized document, otherwise the public lookup
            # reports a mismatch.
            "importe": self._l10n_ar_arca_imp_total(
                self._l10n_ar_get_amounts(base_lines)
            ),
            "moneda": self.currency_id.l10n_ar_afip_code or "PES",
            "ctz": self._l10n_ar_arca_currency_rate(),
            "tipoDocRec": int(
                partner.l10n_latam_identification_type_id.l10n_ar_afip_code or "99"
            ),
            "nroDocRec": partner._get_id_number_sanitize(),
            "tipoCodAut": "E",
            "codAut": int(self.l10n_ar_arca_cae or 0),
        }

    def _l10n_ar_arca_qr_url(self):
        self.ensure_one()
        payload = base64.b64encode(
            json.dumps(self._l10n_ar_arca_qr_data()).encode()
        ).decode()
        return f"https://www.afip.gob.ar/fe/qr/?p={payload}"

    def action_l10n_ar_arca_check_sequence(self):
        """Compare the local journal numbering with the last one authorized by
        ARCA (`FECompUltimoAutorizado`) and warn when they are out of sync.

        Writes nothing: adjusting Odoo numbering outside the normal posting
        flow risks accounting integrity, so this button deliberately does not
        attempt it on its own. It only diagnoses the divergence for a human to
        decide.
        """
        self.ensure_one()
        journal = self.journal_id
        doc_type = self.l10n_latam_document_type_id
        transmissao = self.company_id._l10n_ar_arca_get_transmissao("TransmissaoWSFEv1")
        response = transmissao.fecomp_ultimo_autorizado(
            pto_vta=journal.l10n_ar_afip_pos_number,
            cbte_tipo=int(doc_type.code),
        )
        result = response.FECompUltimoAutorizadoResult
        last_arca_number = result.CbteNro

        last_local_invoice = self.search(
            [
                ("journal_id", "=", journal.id),
                ("l10n_latam_document_type_id", "=", doc_type.id),
                ("state", "=", "posted"),
            ],
            order="l10n_latam_document_number desc",
            limit=1,
        )
        last_local_number = 0
        if last_local_invoice:
            last_local_number = self._l10n_ar_get_document_number_parts(
                last_local_invoice.l10n_latam_document_number, doc_type.code
            )["invoice_number"]

        if last_local_number == last_arca_number:
            raise UserError(
                _(
                    "Numbering in sync: the last one authorized by ARCA and "
                    "the last local one are the same (%(nro)s)."
                )
                % {"nro": last_arca_number}
            )
        raise UserError(
            _(
                "Numbering out of sync for %(journal)s / %(doc_type)s: the "
                "last one authorized by ARCA is %(arca)s and the last local one "
                "is %(local)s. A manual adjustment is required before invoicing "
                "again in this journal."
            )
            % {
                "journal": journal.name,
                "doc_type": doc_type.name,
                "arca": last_arca_number,
                "local": last_local_number,
            }
        )
