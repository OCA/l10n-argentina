# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

{
    "name": "Factura Electrónica Argentina",
    "version": "14.0.1.0.1",
    "category": "Accounting/Localizations",
    "sequence": 14,
    "author": "Nimarosa, ADHOC SA, Moldeo Interactive, Exemax, \
        Codize, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "summary": "Integrate AFIP webservice for Argentina electronic documents",
    "website": "https://github.com/OCA/l10n-argentina",
    "depends": [
        "base",
        "l10n_ar",
        "l10n_latam_invoice_document",
        "l10n_ar_afipws",
        "account_debit_note",
    ],
    "external_dependencies": {
        "python": [
            "OpenSSL",
            "pysimplesoap",
            "pyafipws@https://github.com/reingart/pyafipws/archive/main.zip",
        ]
    },
    "data": [
        "views/account_move_view.xml",
        "views/account_journal_view.xml",
        "views/res_currency.xml",
        # "data/automatic_post_cron.xml",
    ],
    "maintainers": ["nimarosa", "ibuioli"],
    "demo": [],
    "images": [],
    "installable": True,
}
