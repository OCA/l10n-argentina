# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

{
    "name": "Invoice Report - Argentina",
    "version": "14.0.1.0.0",
    "summary": "Advanced invoice report for Argentina localization",
    "author": "Nimarosa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-argentina",
    "license": "LGPL-3",
    "category": "Invoicing",
    "depends": ["l10n_ar_afipws_fe", "report_qweb_pdf_watermark"],
    "data": [
        "views/res_company_views.xml",
        "views/report_invoice_fe_template.xml",
        "views/report_payment_template.xml",
        "views/reports.xml",
    ],
    "installable": True,
    "maintainers": ["Nimarosa"],
}
