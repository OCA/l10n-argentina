# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

{
    "name": "VAT Ledger for Argentina",
    "version": "18.0.1.0.0",
    "category": "Localization/Argentina",
    "license": "AGPL-3",
    "summary": "VAT Ledger, VAT Digital Ledger and VAT Reports for Argentina",
    "author": "Odoo Community Association (OCA), Codize, Exemax, ADHOC SA, "
    "Moldeo Interactive, KMEE",
    "website": "https://github.com/OCA/l10n-argentina",
    "depends": ["l10n_ar", "report_xlsx"],
    "external_dependencies": {},
    "development_status": "Alpha",
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/account_vat_ledger.xml",
        "views/account_vat_ledger_pdf.xml",
        "views/account_vat_ledger_xlsx.xml",
    ],
    "maintainers": ["mileo"],
    "installable": True,
}
