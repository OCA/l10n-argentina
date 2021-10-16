import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo8-addons-oca-l10n-argentina",
    description="Meta package for oca-l10n-argentina Odoo addons",
    version=version,
    install_requires=[
        'odoo8-addon-base_vat_ar',
        'odoo8-addon-l10n_ar_account_check',
        'odoo8-addon-l10n_ar_account_create_check',
        'odoo8-addon-l10n_ar_account_payment',
        'odoo8-addon-l10n_ar_bank_statement',
        'odoo8-addon-l10n_ar_base_country_state',
        'odoo8-addon-l10n_ar_cash_register',
        'odoo8-addon-l10n_ar_chart_of_account',
        'odoo8-addon-l10n_ar_electronic_invoice_storage_rg1361',
        'odoo8-addon-l10n_ar_perceptions_basic',
        'odoo8-addon-l10n_ar_point_of_sale',
        'odoo8-addon-l10n_ar_retentions_basic',
        'odoo8-addon-l10n_ar_sale_order',
        'odoo8-addon-l10n_ar_tax_reports',
        'odoo8-addon-l10n_ar_wsaa',
        'odoo8-addon-l10n_ar_wsfe',
        'odoo8-addon-l10n_ar_wsfe_jasper',
        'odoo8-addon-l10n_ar_wsfe_perceptions',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 8.0',
    ]
)
