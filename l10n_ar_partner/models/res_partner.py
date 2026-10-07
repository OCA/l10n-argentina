import logging

from odoo import models

_logger = logging.getLogger(__name__)

RESP_IVA_MAPPING = {
    "N": "Responsable Monotributo",
    "NI": "Responsable Monotributo",
    "AC": "IVA Responsable Inscripto",
    "S": "IVA Responsable Inscripto",
    "XN": "IVA No Alcanzado",
    "AN": "IVA No Alcanzado",
    "NA": "IVA No Alcanzado",
    "EX": "IVA Sujeto Exento",
}

STATES = {"NEUQUEN": "Neuquén", "CORDOBA": "Córdoba"}


class ResPartner(models.Model):
    _inherit = "res.partner"

    def update_from_padron(self):

        company_id = self.env.company

        if self.l10n_latam_identification_type_id.name == "CUIT":
            ws_sr_padron_a5 = company_id.get_connection("ws_sr_padron_a5").connect()
            # ws_sr_padron_a5.Consultar('20000000516') # Testing
            ws_sr_padron_a5.Consultar(self.vat)

            self.name = ws_sr_padron_a5.denominacion
            self.street = ws_sr_padron_a5.direccion.capitalize()
            self.city = ws_sr_padron_a5.localidad.capitalize()
            self.zip = ws_sr_padron_a5.cod_postal
            self.company_type = (
                "person" if ws_sr_padron_a5.tipo_persona == "FISICA" else "company"
            )

            l10n_ar_type = ""
            l10n_ar_type = RESP_IVA_MAPPING.get(
                ws_sr_padron_a5.imp_iva, "Consumidor Final"
            )

            if l10n_ar_type != "":
                iva_afip = self.env["l10n_ar.afip.responsibility.type"].search(
                    [("name", "=", l10n_ar_type)], limit=1
                )
                self.l10n_ar_afip_responsibility_type_id = iva_afip.id

            if ws_sr_padron_a5.provincia:
                country_id = self.env["res.country"].search(
                    [("name", "=", "Argentina")], limit=1
                )
                if country_id:
                    self.country_id = country_id.id

                provincia = ""
                provincia = STATES.get(
                    ws_sr_padron_a5.provincia, ws_sr_padron_a5.provincia
                )

                state_id = self.env["res.country.state"].search(
                    [("name", "like", provincia), ("country_id", "=", country_id.id)],
                    limit=1,
                )
                if state_id:
                    self.state_id = state_id.id
        else:
            iva_afip = self.env["l10n_ar.afip.responsibility.type"].search(
                [("name", "=", "Consumidor Final")], limit=1
            )
            self.l10n_ar_afip_responsibility_type_id = iva_afip.id
