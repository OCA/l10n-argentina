import logging

from zeep.helpers import serialize_object

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Mapping from AFIP imp_iva codes to Odoo responsibility types
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

# Province name corrections (AFIP returns uppercase without accents)
STATES_MAPPING = {
    "NEUQUEN": "Neuquén",
    "CORDOBA": "Córdoba",
    "TUCUMAN": "Tucumán",
    "ENTRE RIOS": "Entre Ríos",
    "RIO NEGRO": "Río Negro",
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model_create_multi
    def create(self, vals_list):
        # Set Spanish Argentina as default language if not specified
        ar_lang = self.env["res.lang"].search(
            [("code", "=", "es_AR"), ("active", "=", True)], limit=1
        )
        if ar_lang:
            for vals in vals_list:
                if not vals.get("lang"):
                    vals["lang"] = "es_AR"
        return super().create(vals_list)

    def update_from_padron(self):  # noqa: C901
        """
        Update partner data from AFIP Padrón A5 webservice.
        Requires the company to have ws_sr_padron_a5 service configured.
        """
        self.ensure_one()
        company = self.env.company

        # Check if partner has CUIT identification type
        if (
            not self.l10n_latam_identification_type_id
            or self.l10n_latam_identification_type_id.name != "CUIT"
        ):
            # If not CUIT, set as Consumidor Final
            iva_cf = self.env["l10n_ar.afip.responsibility.type"].search(
                [("name", "=", "Consumidor Final")], limit=1
            )
            if iva_cf:
                self.l10n_ar_afip_responsibility_type_id = iva_cf.id
            raise UserError(
                self.env._(
                    "Partner must have CUIT identification type to query AFIP Padrón."
                )
            )

        if not self.vat:
            raise UserError(
                self.env._(
                    "Partner must have a VAT number (CUIT) to query AFIP Padrón."
                )
            )

        # Get connection to ws_sr_padron_a5
        connection = company.get_connection("ws_sr_padron_a5")
        if not connection:
            raise UserError(
                self.env._(
                    "No connection configured for ws_sr_padron_a5. "
                    "Please configure it in the company's AFIP connections."
                )
            )

        # Connect and get AfipWsClient wrapper
        ws = connection.connect()

        # Clean CUIT (remove dashes and spaces)
        cuit = self.vat.replace("-", "").replace(" ", "")
        company_cuit = ws.Cuit.replace("-", "").replace(" ", "") if ws.Cuit else ""

        _logger.info("Querying AFIP Padrón A5 for CUIT %s", cuit)

        try:
            # Call getPersona method using zeep client
            response = ws.client.service.getPersona(
                token=ws.Token,
                sign=ws.Sign,
                cuitRepresentada=company_cuit,
                idPersona=cuit,
            )
        except Exception as e:
            _logger.error("Error querying AFIP Padrón: %s", str(e))
            raise UserError(
                self.env._("Error querying AFIP Padrón: %(error)s", error=str(e))
            ) from e

        # Convert response to dict for logging
        response_dict = serialize_object(response, dict)
        _logger.info("AFIP Padrón response: %s", response_dict)

        if not response:
            raise UserError(
                self.env._("No data returned from AFIP for CUIT %(cuit)s", cuit=cuit)
            )

        # Check if there's an error in the response
        if hasattr(response, "errorConstancia") and response.errorConstancia:
            error = response.errorConstancia
            error_msg = error.error if hasattr(error, "error") else str(error)
            _logger.error("AFIP Padrón error: %s", error_msg)
            raise UserError(self.env._("AFIP Error: %(error)s", error=error_msg))

        # Extract datosGenerales - this is where the main data is
        datos_generales = getattr(response, "datosGenerales", None)
        if not datos_generales:
            raise UserError(
                self.env._(
                    "No datosGenerales in AFIP response for CUIT %(cuit)s", cuit=cuit
                )
            )

        # Track changes for notification
        changes = []

        # Update partner name from datosGenerales
        old_name = self.name
        nombre = getattr(datos_generales, "nombre", None)
        apellido = getattr(datos_generales, "apellido", None)
        razon_social = getattr(datos_generales, "razonSocial", None)
        tipo_persona = getattr(datos_generales, "tipoPersona", None)

        if nombre and apellido:
            # Physical person
            new_name = f"{apellido}, {nombre}".title()
            self.name = new_name
            self.company_type = "person"
            if old_name != new_name:
                changes.append(f"Nombre: {new_name}")
        elif razon_social:
            # Legal person (company)
            new_name = razon_social.title()
            self.name = new_name
            self.company_type = "company"
            if old_name != new_name:
                changes.append(f"Razón Social: {new_name}")

        # Set company type from tipoPersona
        if tipo_persona:
            self.company_type = "person" if tipo_persona == "FISICA" else "company"

        # Update address from domicilioFiscal inside datosGenerales
        domicilio = getattr(datos_generales, "domicilioFiscal", None)
        if domicilio:
            # Street address
            direccion = getattr(domicilio, "direccion", None)
            if direccion:
                old_street = self.street
                self.street = direccion.title()
                if old_street != self.street:
                    changes.append(f"Dirección: {self.street}")

            # City
            localidad = getattr(domicilio, "localidad", None)
            if localidad:
                old_city = self.city
                self.city = localidad.title()
                if old_city != self.city:
                    changes.append(f"Ciudad: {self.city}")

            # ZIP code
            cod_postal = getattr(domicilio, "codPostal", None)
            if cod_postal:
                old_zip = self.zip
                self.zip = cod_postal
                if old_zip != self.zip:
                    changes.append(f"CP: {self.zip}")

            # Province and Country
            provincia = getattr(domicilio, "descripcionProvincia", None)
            if provincia:
                # Apply corrections for accents
                provincia_clean = STATES_MAPPING.get(
                    provincia.upper(), provincia.title()
                )

                country = self.env["res.country"].search([("code", "=", "AR")], limit=1)
                if country:
                    if self.country_id != country:
                        self.country_id = country.id
                        changes.append("País: Argentina")

                    state = self.env["res.country.state"].search(
                        [
                            ("name", "ilike", provincia_clean),
                            ("country_id", "=", country.id),
                        ],
                        limit=1,
                    )
                    if state and self.state_id != state:
                        old_state = self.state_id.name if self.state_id else None
                        self.state_id = state.id
                        if old_state != state.name:
                            changes.append(f"Provincia: {state.name}")

        # Check for IVA status in datosRegimenGeneral
        # AFIP tax codes: 30 = IVA, 32 = IVA EXENTO, 20 = IVA (legacy)
        # Priority: IVA (30) > IVA EXENTO (32) > Monotributo
        imp_iva = None
        iva_exento_found = False
        datos_regimen = getattr(response, "datosRegimenGeneral", None)
        if datos_regimen:
            impuestos = getattr(datos_regimen, "impuesto", None)
            if impuestos:
                for impuesto in impuestos:
                    id_impuesto = str(getattr(impuesto, "idImpuesto", None))
                    estado = getattr(impuesto, "estadoImpuesto", None)
                    # IVA normal (código 30) - highest priority
                    if id_impuesto == "30":
                        if estado == "AC":
                            imp_iva = "AC"  # Activo = IVA Responsable Inscripto
                            break
                        elif estado == "EX":
                            imp_iva = "EX"  # Exento = IVA Sujeto Exento
                            break
                        elif estado in ("XN", "AN", "NA"):
                            imp_iva = estado  # No Alcanzado
                            break
                    # IVA EXENTO (código 32) - mark but keep looking for 30
                    elif id_impuesto == "32" and estado == "AC":
                        iva_exento_found = True
                # If no IVA (30) found but IVA EXENTO (32) exists
                if not imp_iva and iva_exento_found:
                    imp_iva = "EX"

        # Check for Monotributo (only if no IVA status found)
        if not imp_iva:
            datos_monotributo = getattr(response, "datosMonotributo", None)
            if datos_monotributo:
                imp_iva = "N"  # Monotributista

        # Set responsibility type
        if imp_iva:
            l10n_ar_type = RESP_IVA_MAPPING.get(imp_iva, "Consumidor Final")
        else:
            l10n_ar_type = "Consumidor Final"

        old_iva = (
            self.l10n_ar_afip_responsibility_type_id.name
            if self.l10n_ar_afip_responsibility_type_id
            else None
        )
        iva_afip = self.env["l10n_ar.afip.responsibility.type"].search(
            [("name", "=", l10n_ar_type)], limit=1
        )
        if iva_afip and self.l10n_ar_afip_responsibility_type_id != iva_afip:
            self.l10n_ar_afip_responsibility_type_id = iva_afip.id
            if old_iva != l10n_ar_type:
                changes.append(f"Cond. IVA: {l10n_ar_type}")

        # Always set language to es_AR when updating from AFIP
        ar_lang = self.env["res.lang"].search(
            [("code", "=", "es_AR"), ("active", "=", True)], limit=1
        )
        if ar_lang and self.lang != "es_AR":
            self.lang = "es_AR"
            changes.append("Idioma: Español (AR)")

        _logger.info(
            "Partner %s updated from AFIP Padrón. Changes: %s", self.name, changes
        )

        # Build message
        if changes:
            message = self.env._("Datos actualizados:\n") + "\n".join(changes)
        else:
            message = self.env._(
                "No se encontraron cambios. Los datos ya estaban actualizados."
            )

        # Return action to reload the form and show notification
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
            "context": {
                **self.env.context,
                "form_view_initial_mode": "edit",
                "notification_title": self.env._(
                    "AFIP Padrón - CUIT %(cuit)s", cuit=cuit
                ),
                "notification_message": message,
                "notification_type": "success" if changes else "warning",
            },
        }
