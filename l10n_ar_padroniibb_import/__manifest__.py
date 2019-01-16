###############################################################################
#
#    Copyright (c) 2018 Eynes/E-MIPS
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

{
    'name': 'Padron Retenciones y Percepciones',
    'author': 'Eynes/E-MIPS',
    'website': 'www.eynes.com.ar - www.e-mips.com.ar',
    'version': '1.0',
    'depends': [
        'base_vat_ar',
        'l10n_ar_retentions',
        'l10n_ar_perceptions',
    ],
    'category': '',
    'description': "According to AGIP & ARBA fiscal laws, this module allows to automatically import percentages of Retentions and Perceptions",  # noqa
    'data': [
        'views/padron_view.xml',
        'views/perception_view.xml',
        'views/retention_view.xml',
        'wizard/padron_import_view.xml',
        'wizard/padron_mass_update_view.xml',
        'security/ir.model.access.csv',
    ],
    'external_dependencies': {
        'python': [
            'rarfile',
        ],
    },
    'installable': True,
    'application': True,
}
