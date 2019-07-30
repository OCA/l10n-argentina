##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

import psycopg2

__name__ = u"Remove pos.box.concept.type SQL constraint"


def remove_pos_box_concept_type_constraint(cr):
    try:
        cr.execute(
            """
            ALTER TABLE pos_box_concept
            DROP CONSTRAINT pos_box_concept_account_id_uniq_by_type
            """
        )
    except psycopg2.ProgrammingError:
        cr.rollback()

    return True


def migrate(cr, version):
    return remove_pos_box_concept_type_constraint(cr)
