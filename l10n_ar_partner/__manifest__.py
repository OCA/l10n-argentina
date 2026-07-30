# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

{
    "name": "Extra Partner Data and Padrón for Argentina",
    "version": "18.0.1.0.0",
    "category": "Localization/Argentina",
    "license": "AGPL-3",
    "summary": "Extra Partner Data and Padrón for Argentina",
    "author": "Odoo Community Association (OCA), Codize, Exemax, KMEE",
    "website": "https://github.com/OCA/l10n-argentina",
    "depends": ["l10n_ar_arca_ws"],
    "external_dependencies": {
        "python": ["arcalib"],
    },
    "data": ["views/res_partner.xml"],
    "maintainers": ["mileo"],
    "installable": True,
}
