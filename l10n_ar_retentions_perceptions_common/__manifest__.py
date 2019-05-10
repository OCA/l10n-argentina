###############################################################################
#    Copyright (c) 2011-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

{
    "name": "Retentions and Perceptions common (Argentina Retenciones y Percepciones)",
    "version": "11.0.1.0.0",
    "depends": [
        "l10n_ar_account_payment_order",
        "l10n_ar_point_of_sale",
    ],
    "author": "Eynes/E-MIPS",
    "website": "http://eynes.com.ar",
    "license": "AGPL-3",
    "category": "Localisation Modules",
    "description": """
    This module provides:
    Basic data shared between Perceptions and Retentions
    """,
    'data': [
        'security/res_groups_data.xml',
    ],
    'installable': True,
    'application': True,
}
