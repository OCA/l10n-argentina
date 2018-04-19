import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo9-addons-oca-l10n-argentina",
    description="Meta package for oca-l10n-argentina Odoo addons",
    version=version,
    install_requires=[
        'odoo9-addon-l10n_ar_base_country_state',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
