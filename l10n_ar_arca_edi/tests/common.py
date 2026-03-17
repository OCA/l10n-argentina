# Copyright 2026 Leonobitech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import datetime

from odoo.tests.common import TransactionCase


class ArcaEdiTestCommon(TransactionCase):
    """Shared setup for l10n_ar_arca_edi tests.

    Creates a minimal environment with:
    - A test company with Argentine chart of accounts references
    - A mock ARCA certificate record (no real crypto keys)
    - A test journal with ARCA EDI enabled
    - A Consumidor Final partner
    - A CUIT partner (Responsable Inscripto)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # -- Country --
        cls.country_ar = cls.env.ref("base.ar")

        # -- Company: use existing company (has Chart of Accounts) --
        cls.company = cls.env.company
        cls.company.write({
            "country_id": cls.country_ar.id,
            "currency_id": cls.env.ref("base.ARS").id,
        })

        # -- Mock certificate (no real keys, just enough data for logic tests) --
        # We use a dummy PEM-like base64 for private_key / certificate fields.
        # These are NOT valid crypto keys; tests that need signing must mock
        # the crypto calls.
        cls.dummy_pem = base64.b64encode(b"-----BEGIN DUMMY-----\nMOCKDATA\n-----END DUMMY-----\n")

        cls.certificate = cls.env["l10n_ar.arca.certificate"].create({
            "name": "Test Certificate",
            "company_id": cls.company.id,
            "cuit": "20-29318820-4",
            "environment": "testing",
            "state": "active",
            "private_key": cls.dummy_pem,
            "certificate": cls.dummy_pem,
            "wsaa_token": "MOCK_TOKEN_123",
            "wsaa_sign": "MOCK_SIGN_456",
            "wsaa_token_expiration": datetime.datetime(2099, 12, 31, 23, 59, 59),
        })

        # Link certificate to company
        cls.company.l10n_ar_arca_certificate_id = cls.certificate

        # -- Journal --
        cls.journal = cls.env["account.journal"].create({
            "name": "ARCA Sales",
            "type": "sale",
            "code": "ARC",
            "company_id": cls.company.id,
            "l10n_ar_arca_edi_enabled": True,
            "l10n_ar_afip_pos_number": 3,
        })

        # -- Identification types (create minimal records if l10n_ar xmlids
        #    are not loaded, which is common in unit test environments) --
        LatamIdType = cls.env["l10n_latam.identification.type"]

        cls.id_type_cuit = LatamIdType.search(
            [("l10n_ar_afip_code", "=", "80")], limit=1
        )
        if not cls.id_type_cuit:
            cls.id_type_cuit = LatamIdType.create({
                "name": "CUIT",
                "l10n_ar_afip_code": "80",
            })

        cls.id_type_dni = LatamIdType.search(
            [("l10n_ar_afip_code", "=", "96")], limit=1
        )
        if not cls.id_type_dni:
            cls.id_type_dni = LatamIdType.create({
                "name": "DNI",
                "l10n_ar_afip_code": "96",
            })

        # -- AFIP responsibility types (search or create) --
        AfipResp = cls.env["l10n_ar.afip.responsibility.type"]

        cls.resp_ri = AfipResp.search([("code", "=", "1")], limit=1)
        if not cls.resp_ri:
            cls.resp_ri = AfipResp.create({
                "name": "IVA Responsable Inscripto",
                "code": "1",
            })

        cls.resp_cf = AfipResp.search([("code", "=", "5")], limit=1)
        if not cls.resp_cf:
            cls.resp_cf = AfipResp.create({
                "name": "Consumidor Final",
                "code": "5",
            })

        cls.resp_mono = AfipResp.search([("code", "=", "6")], limit=1)
        if not cls.resp_mono:
            cls.resp_mono = AfipResp.create({
                "name": "Responsable Monotributo",
                "code": "6",
            })

        # -- Partners --
        cls.partner_cf = cls.env["res.partner"].create({
            "name": "Consumidor Final Test",
            "company_id": cls.company.id,
            "l10n_ar_afip_responsibility_type_id": cls.resp_cf.id,
            # No VAT / no identification type -> should resolve to doc 99 / 0
        })

        cls.partner_ri = cls.env["res.partner"].create({
            "name": "Empresa RI Test",
            "company_id": cls.company.id,
            "vat": "30-71234567-9",
            "l10n_latam_identification_type_id": cls.id_type_cuit.id,
            "l10n_ar_afip_responsibility_type_id": cls.resp_ri.id,
        })

        cls.partner_dni = cls.env["res.partner"].create({
            "name": "Persona DNI Test",
            "company_id": cls.company.id,
            "vat": "12345678",
            "l10n_latam_identification_type_id": cls.id_type_dni.id,
            "l10n_ar_afip_responsibility_type_id": cls.resp_mono.id,
        })

        # -- Revenue account (needed for invoice lines) --
        # In Odoo 19, account.account uses company_ids (M2M) instead of
        # company_id, so we search without company filter.
        cls.account_revenue = cls.env['account.account'].search([
            ('account_type', '=', 'income'),
        ], limit=1)
        if not cls.account_revenue:
            cls.account_revenue = cls.env['account.account'].search([
                ('account_type', '=', 'income_other'),
            ], limit=1)
        if not cls.account_revenue:
            cls.account_revenue = cls.env['account.account'].create({
                'name': 'Test Revenue',
                'code': '400000',
                'account_type': 'income',
            })

        # Set income account on the default product category so that
        # invoice lines auto-resolve the account from the product.
        default_categ = cls.env.ref('product.product_category_all', raise_if_not_found=False)
        if default_categ:
            default_categ.with_company(cls.company).property_account_income_categ_id = cls.account_revenue

        # -- Document types (Factura C = 11, Nota de Credito C = 13) --
        LatamDocType = cls.env["l10n_latam.document.type"]

        cls.doc_type_fc = LatamDocType.search(
            [("code", "=", "11"), ("country_id", "=", cls.country_ar.id)], limit=1
        )
        if not cls.doc_type_fc:
            cls.doc_type_fc = LatamDocType.create({
                "name": "Factura C",
                "code": "11",
                "country_id": cls.country_ar.id,
            })

        cls.doc_type_fa = LatamDocType.search(
            [("code", "=", "1"), ("country_id", "=", cls.country_ar.id)], limit=1
        )
        if not cls.doc_type_fa:
            cls.doc_type_fa = LatamDocType.create({
                "name": "Factura A",
                "code": "1",
                "country_id": cls.country_ar.id,
            })

        cls.doc_type_nc_c = LatamDocType.search(
            [("code", "=", "13"), ("country_id", "=", cls.country_ar.id)], limit=1
        )
        if not cls.doc_type_nc_c:
            cls.doc_type_nc_c = LatamDocType.create({
                "name": "Nota de Credito C",
                "code": "13",
                "country_id": cls.country_ar.id,
            })

        # An unsupported doc type for negative testing
        cls.doc_type_unsupported = LatamDocType.search(
            [("code", "=", "999"), ("country_id", "=", cls.country_ar.id)], limit=1
        )
        if not cls.doc_type_unsupported:
            cls.doc_type_unsupported = LatamDocType.create({
                "name": "Unsupported Type",
                "code": "999",
                "country_id": cls.country_ar.id,
            })
