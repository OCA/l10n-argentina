# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

{
    "name": "Modulo Base para los Web Services de AFIP",
    "version": "14.0.1.0.1",
    "category": "Accounting/Localizations",
    "sequence": 14,
    "author": "Nimarosa, ADHOC SA, Moldeo Interactive, Exemax, \
         Codize, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "summary": "Integration for Argentina Electronic invoice webservices",
    "depends": [
        "l10n_ar",
    ],
    "external_dependencies": {"python": ["OpenSSL", "pysimplesoap"]},
    "website": "https://github.com/OCA/l10n-argentina",
    "data": [
        "wizard/upload_certificate_view.xml",
        "views/afipws_menuitem.xml",
        "views/afipws_certificate_view.xml",
        "views/afipws_certificate_alias_view.xml",
        "views/afipws_connection_view.xml",
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/res_config_settings.xml",
    ],
    "maintainers": ["nimarosa", "ibuioli"],
    "images": [],
    "installable": True,
    "auto_install": False,
    "application": False,
}
