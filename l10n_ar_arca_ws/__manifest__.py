# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Argentina ARCA Web Services (transport)",
    "version": "18.0.1.0.0",
    "category": "Localization/Argentina",
    "summary": "WSAA authentication and transport for the ARCA (ex AFIP) web services",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-argentina",
    "license": "AGPL-3",
    "development_status": "Beta",
    "depends": [
        "l10n_ar",
        "certificate",
    ],
    "external_dependencies": {
        "python": ["arcalib"],
    },
    "data": [
        "security/ir.model.access.csv",
        "security/l10n_ar_arca_token_security.xml",
        "views/res_company_views.xml",
    ],
    "installable": True,
    "maintainers": ["mileo"],
}
