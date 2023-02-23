import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-l10n-argentina",
    description="Meta package for oca-l10n-argentina Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-l10n_ar_account_move_tax',
        'odoo14-addon-l10n_ar_afipws',
        'odoo14-addon-l10n_ar_afipws_fe',
        'odoo14-addon-l10n_ar_bank',
        'odoo14-addon-l10n_ar_partner',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 14.0',
    ]
)
