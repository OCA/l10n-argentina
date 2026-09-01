# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

{
    "name": "Factura Electronica - Argentina",
    "version": "19.0.1.2.3",
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
            "cryptography",
            "zeep",
            "lxml",
        ]
    },
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_view.xml",
        "views/account_journal_view.xml",
        "views/report_invoice.xml",
        "data/automatic_post_cron.xml",
        "wizard/account_validate_account_move_view.xml",
        "wizard/afip_ws_consult_view.xml",
        "views/res_config_settings.xml",
    ],
    "maintainers": ["nimarosa", "ibuioli"],
    "demo": [],
    "images": [],
    "installable": True,
}
