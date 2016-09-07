# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 Eynes - Ingenieria del software.
#    (http://www.eynes.com.ar) All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Partner Miscellaneous',
    'version': '8.0.0.0.1',
    'category': 'Localisation Modules',
    'description': """
    This Modules brings up some special configurations:

    * Make vat and document_type_id fields required when customer is True.
    """,
    'author': 'Eynes',
    'website': 'http://www.eynes.com.ar/',
    'depends': ['base_vat_ar'],
    'init_xml': [],
    'data': [
        'views/partner_view.xml',
    ],
    'demo_xml': [],
    'test': [],
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
