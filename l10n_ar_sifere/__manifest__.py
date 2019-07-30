###############################################################################
#
#    Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
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
    "name": "SIFERE",
    "category": "L10N AR",
    "version": "11.0.1.0.0",
    "author": "Eynes/E-MIPS",
    "license": "AGPL-3",
    "description": "SIFERE Exporter",
    "depends": [
        "base",
        "l10n_ar_perceptions_basic",
        "l10n_ar_retentions_basic",
        "base_report_exporter",
    ],
    "data": [
        "data/data.xml",
        "wizard/create_sifere_files_view.xml",
        "views/sifere_config_view.xml",
    ],
    "installable": True,
    "application": True,
}
