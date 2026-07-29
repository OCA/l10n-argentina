# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Argentina ARCA Export Invoicing (WSFEXv1)",
    "version": "18.0.1.0.0",
    "category": "Localization/Argentina",
    "summary": "ARCA export electronic invoice (letter E), via WSFEXv1",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-argentina",
    "license": "AGPL-3",
    "development_status": "Beta",
    "depends": [
        "l10n_ar_arca_edi",
    ],
    "external_dependencies": {
        "python": ["arcalib"],
    },
    "data": [
        "views/account_move_views.xml",
        "views/res_country_views.xml",
    ],
    "installable": True,
    "maintainers": ["mileo"],
}
