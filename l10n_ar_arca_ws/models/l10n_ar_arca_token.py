# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
import logging
from datetime import timedelta, timezone

from odoo import _, fields, models
from odoo.exceptions import UserError

from .res_company import AMBIENTE_ODOO_TO_ARCALIB

_logger = logging.getLogger(__name__)

# Safety margin before considering the token expired and forcing a renewal.
# Same margin used inside arcalib (arcalib.transmissao.wsaa._RENEW_MARGIN),
# duplicated here because the database cache is a layer of its own: both exist,
# the arcalib one does not survive a worker restart, this one does.
_RENEW_MARGIN = timedelta(minutes=5)


class L10nArArcaToken(models.Model):
    _name = "l10n_ar.arca.token"
    _description = "ARCA WSAA token/sign, per company/environment/service"
    _rec_name = "servico"

    company_id = fields.Many2one(
        comodel_name="res.company", required=True, ondelete="cascade"
    )
    environment = fields.Selection(
        selection=[("homologacion", "Homologación"), ("produccion", "Producción")],
        required=True,
    )
    servico = fields.Char(
        string="Service",
        required=True,
        help="arcalib endpoint key for the service: wsfev1, wsfexv1, wsbfev1, "
        "wscdc or wspadron_a5 (this is what "
        "`arcalib.transmissao.TransmissaoWSxxx` passes to `get_credentials`, not "
        "the internal `<service>` name of WSAA).",
    )
    token = fields.Char(required=True)
    sign = fields.Char(required=True)
    expiration = fields.Datetime(required=True)

    _sql_constraints = [
        (
            "unique_company_env_servico",
            "unique(company_id, environment, servico)",
            "A token already exists for this company, environment and service.",
        )
    ]

    def _get_wsaa_adapter(self, company):
        """Return an adapter exposing ``get_credentials(service)`` for a company.

        Does not call ARCA here: the call only happens the first time
        ``get_credentials`` is invoked for a service without a valid cached
        token (lazy).
        """
        return _WsaaOdooAdapter(self.env, company)

    def _get_cached(self, company, servico):
        """Cached token and sign, valid for longer than the safety margin, or None."""
        record = self.search(
            [
                ("company_id", "=", company.id),
                ("environment", "=", company.l10n_ar_arca_environment),
                ("servico", "=", servico),
            ],
            limit=1,
        )
        if not record:
            return None
        if fields.Datetime.now() >= record.expiration - _RENEW_MARGIN:
            return None
        return record.token, record.sign

    def _store(self, company, servico, token, sign, expiration):
        record = self.search(
            [
                ("company_id", "=", company.id),
                ("environment", "=", company.l10n_ar_arca_environment),
                ("servico", "=", servico),
            ],
            limit=1,
        )
        vals = {
            "company_id": company.id,
            "environment": company.l10n_ar_arca_environment,
            "servico": servico,
            "token": token,
            "sign": sign,
            "expiration": expiration,
        }
        if record:
            record.write(vals)
        else:
            self.create(vals)
        # No isolated commit here on purpose: an explicit commit is forbidden
        # inside a test (Odoo raises AssertionError) and, outside tests, the
        # write already rides the normal transaction of the request or cron that
        # called get_credentials(). Worst case of not committing separately: an
        # external rollback after obtaining a fresh token wastes that login
        # (ARCA does not document an aggressive rate limit on WSAA for this to
        # be a real problem). It is not a correctness bug, just an occasional
        # extra call.


class _WsaaOdooAdapter:
    """Duck-type of ``arcalib.transmissao.WSAA.get_credentials``, cached in DB.

    Not a `models.Model`: it is a plain Python object, so it can be handed
    straight to ``arcalib.transmissao.TransmissaoWSFEv1`` (and friends) without
    dragging the ORM into the library signature.
    """

    def __init__(self, env, company):
        # Named `self.env` (not `self._env`) on purpose: that is what
        # `odoo.tools.translate._get_lang` looks for in the frame to resolve the
        # language of the `_()` messages raised by this adapter (which is not a
        # `models.Model`, so Odoo cannot find the language by itself). Without
        # it, every `UserError` from here logs a "no translation language
        # detected" WARNING, which fails the OCA checklog even though the
        # exception itself is correct.
        self.env = env
        self._company = company

    def get_credentials(self, servico):
        # Deliberate `sudo()`: the WSAA token is infrastructure, not business
        # data. Whoever invoices needs a valid token but cannot read or write
        # the token table (ACL restricted to `base.group_system`) nor the
        # `certificate.certificate`, which only the administrator can read.
        # Without `sudo()` only the administrator would be able to invoice.
        # The scope stays narrow: `_get_cached`/`_store` always filter by an
        # explicit company and environment, and the company comes from the
        # `account.move` the user was already entitled to post, so elevating
        # here grants no access to another company's token.
        token_model = self.env["l10n_ar.arca.token"].sudo()
        cached = token_model._get_cached(self._company, servico)
        if cached is not None:
            return cached

        wsaa = self._build_arcalib_wsaa()
        # Public API of arcalib >=0.1.1: returns the real expiration, without
        # relying on an internal attribute (`_cache`) of the library.
        token, sign, expiration = wsaa.get_credentials_with_expiration(servico)
        # `expiration` comes with tzinfo (arcalib uses the Buenos Aires offset,
        # UTC-3). `fields.Datetime` stores naive UTC: dropping the tzinfo
        # without converting (the previous bug) made the cache expire three
        # hours early in any positive offset.
        expiration_utc = expiration.astimezone(timezone.utc).replace(tzinfo=None)
        token_model._store(
            self._company,
            servico,
            token,
            sign,
            fields.Datetime.to_string(expiration_utc),
        )
        return token, sign

    def _build_arcalib_wsaa(self):
        try:
            from arcalib.transmissao import config as arcalib_config
            from arcalib.transmissao.wsaa import WSAA
        except ImportError as err:
            raise UserError(
                _(
                    "The 'arcalib' library is not installed. Install it with "
                    "pip install 'arcalib[transmissao]' in the Odoo environment."
                )
            ) from err

        # `sudo()` for the same reason as in `get_credentials`: the ARCA
        # certificate and private key are only readable by `base.group_system`
        # in the core, and whoever invoices has to sign the ticket without being
        # an administrator.
        company = self._company.sudo()
        certificate = company.l10n_ar_arca_certificate_id
        if not certificate:
            raise UserError(_("Set the ARCA certificate on company %s.") % company.name)
        if not certificate.private_key_id:
            raise UserError(
                _("The ARCA certificate of company %s has no private key linked.")
                % company.name
            )

        cert_pem = base64.b64decode(
            certificate.with_context(bin_size=False).pem_certificate
        )
        key_pem = base64.b64decode(
            certificate.private_key_id.with_context(bin_size=False).pem_key
        )
        ambiente = getattr(
            arcalib_config, AMBIENTE_ODOO_TO_ARCALIB[company.l10n_ar_arca_environment]
        )
        return WSAA(ambiente, cert_pem, key_pem)
