# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Argentina ARCA Electronic Invoicing (WSFEv1)",
    "version": "18.0.1.0.0",
    "category": "Localization/Argentina",
    "summary": "ARCA (ex AFIP) electronic invoice via WSFEv1, domestic market",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-argentina",
    "license": "AGPL-3",
    "development_status": "Beta",
    "depends": [
        "l10n_ar_arca_ws",
    ],
    "external_dependencies": {
        "python": ["arcalib"],
    },
    "data": [
        "views/account_move_views.xml",
        "views/account_journal_views.xml",
        "report/invoice_qr_report.xml",
    ],
    "installable": True,
    "maintainers": ["mileo"],
}
