# -*- coding: utf-8 -*-
import psycopg2
import logging

logger = logging.getLogger(__name__)


def _do_update(cr, installed_version):
    try:
        q = """
            CREATE TABLE pos_denomination(
                pos_ar_id integer,
                denomination_id integer
            )
        """
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
