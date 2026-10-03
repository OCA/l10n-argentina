# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_ar_arca_edi.models.account_move import L10nArArcaRejection


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ar_arca_tipo_expo = fields.Selection(
        selection=[
            ("1", "1 - Exportación definitiva de bienes"),
            ("2", "2 - Servicios"),
            ("4", "4 - Otros (exportación)"),
        ],
        string="Export type (WSFEXv1)",
        help="TO BE VERIFIED: the mapping was not confirmed against the official "
        "ARCA specification for WSFEXv1 (Tipo_expo). Manual entry until that "
        "verification. See readme/ROADMAP.rst.",
    )

    l10n_ar_arca_permiso_existente = fields.Selection(
        selection=[("S", "S - Sí"), ("N", "N - No")],
        string="Existing shipping permit",
        default="N",
        help="Mandatory on the definitive export of goods (Tipo_expo = 1): "
        "states whether a shipping permit exists for the document. Sending the "
        "permit detail (Permisos array of WSFEXv1) is not implemented yet, which "
        "is why marking 'S' is refused: see readme/ROADMAP.rst.",
    )

    # `Tipo_expo` requiring the permiso de embarque to be declared:
    # 1 = exportación definitiva de bienes. Services (2) and others (4) have
    # no permiso.
    L10N_AR_ARCA_TIPO_EXPO_BIENES = "1"

    @api.depends("l10n_latam_document_type_id")
    def _compute_l10n_ar_arca_is_export(self):
        for move in self:
            move.l10n_ar_arca_is_export = (
                move.l10n_latam_document_type_id.l10n_ar_letter == "E"
            )

    # `Idioma_cbte` of WSFEXv1: language the document is issued in.
    # 1 = Spanish, the only one that makes sense for a document issued in
    # Argentina (the other values exist to allow issuing in English or
    # Portuguese at the foreign customer's request, a scenario this module does
    # not expose yet: see readme/ROADMAP.rst).
    L10N_AR_ARCA_IDIOMA_ESPANOL = 1

    l10n_ar_arca_is_export = fields.Boolean(
        compute="_compute_l10n_ar_arca_is_export",
        string="Is export",
        help="Letter E (exportación): the CAE request goes to WSFEXv1 instead of "
        "WSFEv1.",
    )

    def _l10n_ar_arca_webservice(self):
        """Letter E goes to WSFEXv1; everything else follows the chain."""
        self.ensure_one()
        if self.l10n_ar_arca_is_export:
            return "wsfexv1"
        return super()._l10n_ar_arca_webservice()

    def _l10n_ar_arca_request_cae_wsfexv1(self):
        """Export document (WSFEXv1).

        The common preconditions (already has a CAE, is not posted) live in
        `_l10n_ar_arca_request_cae` of l10n_ar_arca_edi: only what is specific
        to exports belongs here.
        """
        self.ensure_one()
        if not self.l10n_ar_arca_tipo_expo:
            raise UserError(
                _("Fill in the 'Tipo de exportación' before requesting the CAE.")
            )

        transmissao = self.company_id._l10n_ar_arca_get_transmissao(
            "TransmissaoWSFEXv1"
        )
        cmp = self._l10n_ar_arca_build_fex_request()
        response = transmissao.fex_authorize(cmp)
        self._l10n_ar_arca_process_fex_response(response)

    def _l10n_ar_arca_get_cuit_pais(self):
        """CUIT País: ARCA's own per-country code, distinct from the country
        code `l10n_ar_afip_code`, mandatory in WSFEXv1.

        Has to be configured by hand in `res.country.l10n_ar_arca_cuit_pais`
        (see that field and this module's readme/ROADMAP.rst: there is no
        reliable source at hand to populate the whole table).
        """
        self.ensure_one()
        country = self.partner_id.country_id
        cuit_pais = country.l10n_ar_arca_cuit_pais
        if not cuit_pais:
            raise UserError(
                _(
                    "Set the 'CUIT País (ARCA)' of country %(country)s before "
                    "requesting the export CAE for this contact."
                )
                % {"country": country.name or _("(no country)")}
            )
        return int(cuit_pais)

    def _l10n_ar_arca_build_fex_request(self):
        self.ensure_one()
        from decimal import Decimal

        from arcalib.wsfexv1.bindings.wsfexv1 import ClsFexrequest

        journal = self.journal_id
        partner = self.partner_id
        doc_number_parts = self._l10n_ar_get_document_number_parts(
            self.l10n_latam_document_number, self.l10n_latam_document_type_id.code
        )

        moneda_ctz = (
            1.0
            if self.currency_id == self.company_id.currency_id
            else 1 / (self.invoice_currency_rate or 1.0)
        )

        items, items_total = self._l10n_ar_arca_build_items()

        # Fields in the same order the WSFEXv1 XSD declares them (see
        # `ClsFexrequest` in `arcalib/wsfexv1/bindings/wsfexv1.py`), so the
        # payload can be read side by side with the ARCA specification.
        return ClsFexrequest(
            Id=int(self.id),
            Fecha_cbte=self.invoice_date.strftime("%Y%m%d")
            if self.invoice_date
            else None,
            Cbte_Tipo=int(self.l10n_latam_document_type_id.code),
            Punto_vta=journal.l10n_ar_afip_pos_number,
            Cbte_nro=doc_number_parts["invoice_number"],
            Tipo_expo=int(self.l10n_ar_arca_tipo_expo),
            Permiso_existente=self._l10n_ar_arca_permiso_existente_value(),
            Dst_cmp=int(partner.country_id.l10n_ar_afip_code or 0),
            Cliente=partner.name,
            Cuit_pais_cliente=self._l10n_ar_arca_get_cuit_pais(),
            Domicilio_cliente=self._l10n_ar_arca_build_domicilio_cliente(),
            Id_impositivo=partner.vat or None,
            Moneda_Id=self.currency_id.l10n_ar_afip_code or "DOL",
            Moneda_ctz=Decimal(str(moneda_ctz)),
            # Total summed from the items themselves, not `amount_total`:
            # WSFEXv1 validates that the header matches the detail, and the
            # `Items` array has nowhere to carry tax.
            # `_l10n_ar_arca_build_items` already refuses an invoice whose
            # accounting total cannot be represented.
            Imp_total=Decimal(str(items_total)),
            Idioma_cbte=self.L10N_AR_ARCA_IDIOMA_ESPANOL,
            Items=items,
        )

    def _l10n_ar_arca_permiso_existente_value(self):
        """`Permiso_existente` of WSFEXv1, or None when it does not apply.

        ARCA requires the field on the definitive export of goods and does not
        accept it on the other types.
        """
        self.ensure_one()
        if self.l10n_ar_arca_tipo_expo != self.L10N_AR_ARCA_TIPO_EXPO_BIENES:
            return None
        if self.l10n_ar_arca_permiso_existente == "S":
            raise UserError(
                _(
                    "This version of the module does not send the shipping "
                    "permit detail (Permisos array of WSFEXv1), so declaring "
                    "'Permiso de embarque existente' = S is not possible: ARCA "
                    "would reject the document for the missing detail."
                )
            )
        return "N"

    def _l10n_ar_arca_build_domicilio_cliente(self):
        """Foreign customer address on a single line, for `Domicilio_cliente`.

        Uses the core address formatter (`res.partner._display_address`), which
        honours the address layout configured for the destination country, and
        collapses the line breaks because the webservice field is single line.
        """
        self.ensure_one()
        address = self.partner_id._display_address(without_company=True) or ""
        return (
            ", ".join(part.strip() for part in address.splitlines() if part.strip())
            or None
        )

    def _l10n_ar_arca_build_items(self):
        """`Items` array of WSFEXv1 (mandatory: detail of what was exported).

        The field names (`Pro_ds`, `Pro_qty`, `Pro_umed`, ...) are dictated by
        the ARCA WSDL and come from the xsdata generated binding
        (`arcalib.wsfexv1.bindings.wsfexv1.Item`).

        The lines come from the core `_get_rounded_base_and_tax_lines()`
        (LGPL-3), the same source used for the header totals. Two advantages
        over iterating `invoice_line_ids` by hand: sections and notes are
        already excluded (the core does not treat them as base lines), and the
        per line amounts stay consistent with the `Imp_total` being sent,
        avoiding a rounding mismatch between item and header.

        Returns `(ArrayOfItem or None, items total)`. The total comes from here
        because it is the sum of the items that WSFEXv1 validates against the
        header.
        """
        self.ensure_one()
        from arcalib.wsfexv1.bindings.wsfexv1 import ArrayOfItem, Item

        base_lines, _tax_lines = self._get_rounded_base_and_tax_lines()

        items = []
        items_total = 0.0
        for base_line in base_lines:
            # Core technical lines (early payment discount, cash rounding)
            # are not exported goods and have no unit of measure: letting them
            # into the loop broke on the AFIP UoM code requirement. They stay
            # out of the array; if they move the total, the check at the end
            # refuses the invoice with a clear message.
            if base_line["special_type"]:
                continue
            line = base_line["record"]
            uom = base_line["product_uom_id"]
            if not uom.l10n_ar_afip_code:
                raise UserError(
                    _(
                        "The unit of measure '%(uom)s' has no AFIP code. Set "
                        "it before invoicing an export."
                    )
                    % {"uom": uom.display_name or _("(no unit)")}
                )

            # Line amount already net, computed by the core.
            total_item = base_line["tax_details"]["raw_total_excluded_currency"]
            # Bonificacion: WSFEXv1 asks for the discount as an absolute
            # amount while Odoo stores a percentage. The difference between
            # gross (price x quantity) and net is the discount in currency.
            gross = base_line["price_unit"] * base_line["quantity"]
            discount_amount = gross - total_item
            items_total += total_item

            items.append(
                Item(
                    Pro_codigo=line.product_id.default_code or None,
                    Pro_ds=line.name,
                    Pro_qty=base_line["quantity"],
                    Pro_umed=int(uom.l10n_ar_afip_code),
                    Pro_precio_uni=base_line["price_unit"],
                    Pro_bonificacion=discount_amount,
                    Pro_total_item=total_item,
                )
            )
        items_total = self.currency_id.round(items_total)
        # WSFEXv1 has no field for tax: an export document is detail plus
        # total, nothing else. If the accounting total of the invoice is not
        # equal to the sum of the items, the document holds something the
        # webservice cannot represent (a tax, a perception, cash rounding, an
        # embedded early payment discount). Sending it anyway would make ARCA
        # reject it for a mismatch between total and detail, with a message
        # that helps nobody: better to refuse here, naming what is left over.
        if self.currency_id.compare_amounts(items_total, self.amount_total) != 0:
            raise UserError(
                _(
                    "The total of this export invoice (%(total)s) does not "
                    "match the sum of the items (%(items)s). WSFEXv1 only "
                    "carries items and total, with no field for taxes, "
                    "perceptions, cash rounding or early payment discount. "
                    "Remove whatever is adding up outside the items before "
                    "requesting the CAE."
                )
                % {
                    "total": self.amount_total,
                    "items": items_total,
                }
            )
        if not items:
            return None, items_total
        return ArrayOfItem(Item=items), items_total

    def _l10n_ar_arca_process_fex_response(self, response):
        self.ensure_one()
        result = response.FEXAuthorizeResult
        auth = result.FEXResultAuth if result else None
        if not auth:
            raise UserError(_("Unexpected response from ARCA (WSFEXv1): no result."))

        if auth.Resultado != "A":
            # Same contract as the WSFEv1 path: nothing is written before
            # raising, because `_post` wraps the authorization in a savepoint
            # and any write here would be rolled back. The verdict travels in
            # the exception and is persisted by
            # `_l10n_ar_arca_log_cae_failure`.
            raise L10nArArcaRejection(
                _("ARCA rejected the export CAE request (%(resultado)s): %(obs)s")
                % {
                    "resultado": auth.Resultado,
                    "obs": auth.Motivos_Obs or _("no detail"),
                },
                resultado=auth.Resultado,
                observations=auth.Motivos_Obs,
            )

        self.write(
            {
                "l10n_ar_arca_cae": auth.Cae,
                "l10n_ar_arca_cae_due_date": fields.Date.from_string(
                    f"{auth.Fch_venc_Cae[:4]}-{auth.Fch_venc_Cae[4:6]}-{auth.Fch_venc_Cae[6:8]}"
                ),
                "l10n_ar_arca_result": auth.Resultado,
                "l10n_ar_arca_observations": auth.Motivos_Obs,
            }
        )
