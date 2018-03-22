# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2016-TODAY Eynes (http://www.eynes.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import psycopg2

__name__ = u"Store City name"

"""Because city field is now related to city_id.name on res.partner and res.company we relate the
city_id's name to the partners which already have the city_id field set."""


def relate_city_name(cr):
    """Relates city column to city_id.name"""

    try:
        cr.execute(
            """
            UPDATE res_partner
            SET city = c.name
            FROM res_city AS c
            WHERE c.id = res_partner.city_id
            """
        )
    except psycopg2.ProgrammingError:
        cr.rollback()

    return True


def migrate(cr, version):
    return relate_city_name(cr)
