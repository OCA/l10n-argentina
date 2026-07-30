import logging
import unicodedata

from odoo import models

_logger = logging.getLogger(__name__)

# Codes as defined by the core l10n_ar data
# (l10n_ar/data/l10n_ar_afip_responsibility_type_data.xml). Matching by `code`
# instead of the textual `name` is more stable, and the core already guarantees
# these codes.
_RESPONSIBILITY_CODE_MONOTRIBUTO = "6"
_RESPONSIBILITY_CODE_RESPONSABLE_INSCRIPTO = "1"
_RESPONSIBILITY_CODE_CONSUMIDOR_FINAL = "5"

# ARCA code (l10n_latam.identification.type.l10n_ar_afip_code) of the CUIT.
# `name` is a translatable field: comparing by it classified partners holding a
# CUIT as CUIT-less in bulk on an es_AR database.
_IDENTIFICATION_AFIP_CODE_CUIT = "80"

# Known differences between the province name the padrón A5 returns
# (uppercase, unaccented) and the name in `res.country.state`, which also
# differs structurally and not only in accents (the padrón drops "de", for
# instance). The remaining 24 jurisdictions are matched by accent and case
# normalization (see `_normalize_province_name`); this list only covers the
# cases normalization cannot resolve. Not verified against a real padrón A5
# sample (TO BE VERIFIED once a real CUIT is available in homologación).
_PROVINCIA_PADRON_TO_STATE_NAME = {
    "CIUDAD AUTONOMA BUENOS AIRES": "Ciudad Autónoma de Buenos Aires",
}


def _normalize_province_name(text):
    """Uppercase, unaccented, stripped.

    Lets the province name from the padrón (uppercase, unaccented) be compared
    against `res.country.state.name` (accented, normally capitalized) without
    relying on `like`, which does not resolve accent differences.
    """
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).upper().strip()


class ResPartner(models.Model):
    _inherit = "res.partner"

    def update_from_padron(self):
        """Update the partner data from the ARCA padrón A5.

        Rewritten during the 14.0 -> 18.0 migration: the original version
        called `company_id.get_connection("ws_sr_padron_a5")` from the
        `l10n_ar_afipws` module (pyafipws/pysimplesoap, not migrated to 18.0).
        This version uses `l10n_ar_arca_ws` (WSAA) plus `arcalib` (padrón A5
        bindings): the same official ARCA webservice, a different library.

        VAT responsibility is only overwritten when the padrón returns an
        unambiguous signal (monotributo, or the general regime with an active
        tax whose description contains "IVA"). Otherwise the field is NOT
        touched: deciding a taxpayer's responsibility by heuristic is the kind
        of automation that suggests, it does not apply itself.
        """
        for partner in self:
            if (
                partner.l10n_latam_identification_type_id.l10n_ar_afip_code
                != _IDENTIFICATION_AFIP_CODE_CUIT
            ):
                partner._update_from_padron_without_cuit()
                continue
            partner._update_from_padron_with_cuit()

    def _update_from_padron_with_cuit(self):
        self.ensure_one()
        company = self.env.company
        transmissao = company._l10n_ar_arca_get_transmissao(
            "TransmissaoWSPadronA5", cuit_kwarg="cuit_representada"
        )
        id_persona = self._get_id_number_sanitize()
        response = transmissao.get_persona(id_persona=id_persona)
        persona = response.personaReturn
        if not persona or persona.errorConstancia:
            _logger.info(
                "Padrón A5 returned no data for CUIT %s (partner %s).",
                self.vat,
                self.display_name,
            )
            return

        datos = persona.datosGenerales
        if not datos:
            return

        self.name = datos.razonSocial or " ".join(
            filter(None, [datos.nombre, datos.apellido])
        )
        self.company_type = "person" if datos.tipoPersona == "FISICA" else "company"

        domicilio = datos.domicilioFiscal
        if domicilio:
            self.street = (domicilio.direccion or "").title() or self.street
            self.city = (domicilio.localidad or "").title() or self.city
            self.zip = domicilio.codPostal or self.zip
            self._update_state_from_padron(domicilio.descripcionProvincia)

        self._update_responsibility_from_padron(persona)

    def _update_from_padron_without_cuit(self):
        # Sem CUIT identificado: mesma decisão da versão 14.0 deste módulo,
        # tratar como Consumidor Final por padrão.
        self.ensure_one()
        responsibility = self.env["l10n_ar.afip.responsibility.type"].search(
            [("code", "=", _RESPONSIBILITY_CODE_CONSUMIDOR_FINAL)], limit=1
        )
        if responsibility:
            self.l10n_ar_afip_responsibility_type_id = responsibility.id

    def _update_state_from_padron(self, provincia):
        self.ensure_one()
        if not provincia:
            return
        country = self.env.ref("base.ar", raise_if_not_found=False)
        if not country:
            return
        self.country_id = country.id

        provincia_alias = _PROVINCIA_PADRON_TO_STATE_NAME.get(
            _normalize_province_name(provincia)
        )
        provincia_norm = _normalize_province_name(provincia_alias or provincia)
        states = self.env["res.country.state"].search([("country_id", "=", country.id)])
        state = states.filtered(
            lambda s, provincia_norm=provincia_norm: (
                _normalize_province_name(s.name) == provincia_norm
            )
        )
        if state:
            self.state_id = state[:1].id
        else:
            _logger.info(
                "Padrón A5 devolveu província '%s' sem correspondência em "
                "res.country.state for %s; state_id left unchanged.",
                provincia,
                self.display_name,
            )

    def _update_responsibility_from_padron(self, persona):
        self.ensure_one()
        code = None
        if persona.datosMonotributo:
            code = _RESPONSIBILITY_CODE_MONOTRIBUTO
        elif persona.datosRegimenGeneral and any(
            "IVA" in (imp.descripcionImpuesto or "").upper()
            and (imp.estadoImpuesto or "").upper() in ("AC", "ACTIVO")
            for imp in persona.datosRegimenGeneral.impuesto
        ):
            code = _RESPONSIBILITY_CODE_RESPONSABLE_INSCRIPTO

        if code is None:
            _logger.info(
                "Padrón A5 gave no unambiguous VAT responsibility signal for "
                "%s; field left unchanged, review it manually.",
                self.display_name,
            )
            return

        responsibility = self.env["l10n_ar.afip.responsibility.type"].search(
            [("code", "=", code)], limit=1
        )
        if responsibility:
            self.l10n_ar_afip_responsibility_type_id = responsibility.id
