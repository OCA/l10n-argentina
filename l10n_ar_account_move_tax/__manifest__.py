{
    "name": "Account Move Tax",
    "version": "14.0.1.3.0",
    "category": "Localization/Argentina",
    "sequence": 14,
    "author": "Nimarosa, ADHOC SA, Moldeo Interactive, Exemax, \
         Codize, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "summary": "",
    "website": "https://github.com/OCA/l10n-argentina",
    "depends": [
        "l10n_ar_afipws",
        "uom",
        "l10n_latam_invoice_document",
        "l10n_ar",
        "account",
    ],
    "external_dependencies": {},
    "data": [
        "views/account_move_view.xml",
        "security/ir.model.access.csv",
    ],
    "maintainers": ["nimarosa", "ibuioli"],
    "demo": [],
    "images": [],
    "installable": True,
    "auto_install": False,
    "application": False,
}
