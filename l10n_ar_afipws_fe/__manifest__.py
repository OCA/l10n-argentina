# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

{
    "name": "Factura Electrónica - Argentina",
    "version": "16.0.1.0.0",
    "category": "Accounting/Localizations",
    "sequence": 14,
    "author": "Nimarosa, ADHOC SA, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "summary": "Integrate AFIP webservice for Argentina electronic documents",
    "website": "https://github.com/OCA/l10n-argentina",
    "depends": [
        "l10n_ar",
        "l10n_ar_afipws",
        "account_debit_note",
    ],
    "external_dependencies": {
        "python": [
            "OpenSSL",
            "pysimplesoap",
            "future",
            # "pyafipws@https://github.com/reingart/pyafipws/archive/main.zip",
        ]
    },
    "data": [
        "views/account_move_view.xml",
        "views/account_journal_view.xml",
        "views/res_config_settings.xml",
        "data/automatic_post_cron.xml",
        "wizard/account_validate_account_move_view.xml",
    ],
    "maintainers": ["nimarosa", "ibuioli"],
    "demo": [],
    "images": [],
    "installable": True,
}
