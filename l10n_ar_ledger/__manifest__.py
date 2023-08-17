# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

{
    "name": "VAT Ledger for Argentina",
    "version": "14.0.0.0.3",
    "category": "Accounting",
    "license": "AGPL-3",
    "summary": "VAT Ledger, VAT Digital Ledger and VAT Reports for Argentina",
    "author": "Odoo Community Association (OCA), Codize, Exemax, ADHOC SA, Moldeo Interactive",
    "website": "https://github.com/OCA/l10n-argentina",
    "depends": ["base", "l10n_ar", "report_xlsx"],
    "external_dependencies": {},
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/account_vat_ledger.xml",
        "views/account_vat_ledger_pdf.xml",
        "views/account_vat_ledger_xlsx.xml",
    ],
    "maintainers": ["nimarosa", "ibuioli"],
    "installable": True,
}
