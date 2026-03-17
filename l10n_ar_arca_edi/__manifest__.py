# Copyright 2026 Leonobitech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Argentina - ARCA Electronic Invoicing",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Electronic invoicing integration with ARCA (ex-AFIP) for Argentina",
    "development_status": "Beta",
    "author": "Leonobitech, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-argentina",
    "license": "AGPL-3",
    "maintainers": ["felixfigueroa"],
    "countries": ["ar"],
    "depends": [
        "l10n_ar",
        "account_edi",
    ],
    "external_dependencies": {
        "python": [
            "cryptography",
            "zeep",
            "lxml",
        ],
    },
    "data": [
        "security/ir.model.access.csv",
        "data/paperformat.xml",
        "wizards/l10n_ar_arca_certificate_wizard_views.xml",
        "views/l10n_ar_arca_certificate_views.xml",
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
        "views/account_journal_views.xml",
        "reports/report_invoice.xml",
        "data/ir_cron_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_ar_arca_edi/static/src/scss/arca_badge.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
}
