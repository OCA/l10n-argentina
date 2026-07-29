# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Argentina ARCA Document Verification (WSCDC)",
    "version": "18.0.1.0.0",
    "category": "Localization/Argentina",
    "summary": "Check vendor documents against ARCA (WSCDC)",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-argentina",
    "license": "AGPL-3",
    "development_status": "Beta",
    "depends": [
        "l10n_ar_arca_ws",
    ],
    "external_dependencies": {
        "python": ["arcalib"],
    },
    "data": [
        "views/account_move_views.xml",
    ],
    "installable": True,
    "maintainers": ["mileo"],
}
