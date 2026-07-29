# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Maps the value of the `l10n_ar_arca_environment` Selection field to the name
# of the integer attribute exported by `arcalib.transmissao`
# (HOMOLOGACION/PRODUCCION). Single source: `l10n_ar_arca_token.py` imports this
# dict instead of duplicating it.
AMBIENTE_ODOO_TO_ARCALIB = {
    "homologacion": "HOMOLOGACION",
    "produccion": "PRODUCCION",
}


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ar_arca_certificate_id = fields.Many2one(
        comodel_name="certificate.certificate",
        string="ARCA Certificate",
        check_company=True,
        help="Certificate registered on the ARCA portal (WSAA), used to sign the "
        "Login Ticket Request. It must have a private key linked.",
    )
    l10n_ar_arca_environment = fields.Selection(
        selection=[
            ("homologacion", "Homologación (testing)"),
            ("produccion", "Producción"),
        ],
        string="ARCA Environment",
        default="homologacion",
        required=True,
        help="Homologación is the ARCA testing environment: it never issues a "
        "legally valid CAE. Switch to Producción only after validating with real "
        "documents together with the customer.",
    )

    def _l10n_ar_arca_get_wsaa_adapter(self):
        """Return the ARCA credentials adapter (WSAA) for this company.

        The returned object implements ``get_credentials(service)``, the same
        duck-typed interface exposed by ``arcalib.transmissao.WSAA``, so it can
        be passed straight to ``arcalib.transmissao.TransmissaoWSFEv1`` and
        friends. It caches token and sign in the database (model
        ``l10n_ar.arca.token``), surviving a worker restart, and only calls ARCA
        when the cached token has expired.
        """
        self.ensure_one()
        return self.env["l10n_ar.arca.token"]._get_wsaa_adapter(self)

    def _l10n_ar_arca_get_cuit(self):
        """Company CUIT normalized to `int`, without separators.

        `res.partner.vat` keeps the value formatted the way it was typed
        ("30-71234567-8"), while every `TransmissaoWSxxx` class of arcalib
        expects an `int`. Using the core helper (`_get_id_number_sanitize`)
        instead of `int(company.vat)` avoids a `ValueError` on a formatted CUIT.
        """
        self.ensure_one()
        cuit = self.partner_id._get_id_number_sanitize()
        if not cuit:
            raise UserError(_("Set the CUIT of company %s.") % self.name)
        return cuit

    @api.model
    def _l10n_ar_arca_import_transmissao_module(self):
        """Import `arcalib.transmissao`, with a friendly error when the library
        is missing.

        Single import point: the satellite modules (`l10n_ar_arca_edi`,
        `l10n_ar_arca_edi_export`, `l10n_ar_arca_verify`, `l10n_ar_partner`)
        never import `arcalib` directly, and therefore never repeat this guard.
        """
        try:
            from arcalib import transmissao
        except ImportError as err:
            raise UserError(
                _(
                    "The 'arcalib' library is not installed. Install it with "
                    "pip install 'arcalib[transmissao]' in the Odoo environment."
                )
            ) from err
        return transmissao

    def _l10n_ar_arca_get_transmissao(self, transmissao_cls_name, cuit_kwarg="cuit"):
        """Instantiate an arcalib `TransmissaoWSxxx` class for this company.

        Resolves in a single place the environment, the WSAA adapter (with the
        database token cache) and the normalized CUIT.

        `transmissao_cls_name` is the attribute name in `arcalib.transmissao`
        (for instance "TransmissaoWSFEv1"). `cuit_kwarg` exists because
        `TransmissaoWSPadronA5` names its parameter `cuit_representada` instead
        of `cuit`: it is the only naming divergence among the arcalib classes.
        """
        self.ensure_one()
        transmissao_module = self._l10n_ar_arca_import_transmissao_module()
        transmissao_cls = getattr(transmissao_module, transmissao_cls_name)
        ambiente = getattr(
            transmissao_module, AMBIENTE_ODOO_TO_ARCALIB[self.l10n_ar_arca_environment]
        )
        return transmissao_cls(
            ambiente=ambiente,
            wsaa=self._l10n_ar_arca_get_wsaa_adapter(),
            **{cuit_kwarg: self._l10n_ar_arca_get_cuit()},
        )
