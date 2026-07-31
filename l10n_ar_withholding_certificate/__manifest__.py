# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Argentina Withholding Certificate",
    "version": "18.0.1.0.0",
    "category": "Localization/Argentina",
    "summary": "Withholding certificate PDF from the vendor payment",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-argentina",
    "license": "AGPL-3",
    "development_status": "Beta",
    "depends": [
        "l10n_ar_withholding",
    ],
    "data": [
        "data/ir_sequence_data.xml",
        "views/account_payment_views.xml",
        "report/withholding_certificate_report.xml",
    ],
    "installable": True,
    "maintainers": ["mileo"],
}
