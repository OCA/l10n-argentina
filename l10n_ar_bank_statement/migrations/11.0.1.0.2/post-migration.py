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

__name__ = u"Remove pos.box.concept.type SQL constraint"


def remove_pos_box_concept_type_constraint(cr):
    try:
        cr.execute(
            "ALTER TABLE pos_box_concept DROP CONSTRAINT pos_box_concept_account_id_uniq_by_type"
        )
    except psycopg2.ProgrammingError:
        cr.rollback()

    return True


def migrate(cr, version):
    return remove_pos_box_concept_type_constraint(cr)
