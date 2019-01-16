###############################################################################
#   Copyright (c) 2017-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import psycopg2
import logging

logger = logging.getLogger(__name__)


def _do_update(cr, installed_version):
    """
    1. Store relation between pos_ar & denominations
    """
    try:
        q = """
            CREATE TABLE old_denomination(
                pos_ar_id integer,
                pos_ar_name varchar,
                denomination_id integer,
                shop_id integer,
                den_name varchar,
                den_desc varchar,
                new_pos_ar_id integer
            )
        """
        cr.execute(q)
        q = """
            WITH q1 AS (
                SELECT pa.id pos_ar_id, idd.id denomination_id, pa.shop_id,
                    idd.name den_name, idd.desc den_desc, pa.name pos_ar_name
                FROM pos_ar pa
                JOIN invoice_denomination idd ON pa.denomination_id=idd.id
            ) INSERT INTO old_denomination (
                pos_ar_id, denomination_id, shop_id, den_name, den_desc, pos_ar_name)
            SELECT
                pos_ar_id, denomination_id, shop_id, den_name, den_desc, pos_ar_name
            FROM q1
        """
        cr.execute(q)
    except psycopg2.ProgrammingError as e:
        logger.warning(e)
        cr.rollback()
    except Exception as e:
        logger.warning(e)
        cr.rollback()
    else:
        cr.commit()


def migrate(cr, installed_version):
    return _do_update(cr, installed_version)
