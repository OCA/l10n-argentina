# -*- coding: utf-8 -*-
import psycopg2
import logging

logger = logging.getLogger(__name__)


def _do_update(cr, installed_version):
    try:
        logger.info("Updating reference of pos_ar_wsfe_rel")
        q = """
            WITH qa AS (
                SELECT pawr.wsfe_config_id wsfe_config_id, od.new_pos_ar_id pos_ar_id
                FROM pos_ar_wsfe_rel pawr
                JOIN old_denomination od
                ON od.pos_ar_id = pawr.pos_ar_id
            )
            UPDATE pos_ar_wsfe_rel pawr
            SET pos_ar_id=qa.pos_ar_id
            FROM qa WHERE qa.wsfe_config_id=pawr.wsfe_config_id
        """
        cr.execute(q)
        logger.info("Updating reference of pos_ar_wsfex_rel")
        q = """
            WITH qa AS (
                SELECT pawr.wsfex_config_id wsfex_config_id, od.new_pos_ar_id pos_ar_id
                FROM pos_ar_wsfex_rel pawr
                JOIN old_denomination od
                ON od.pos_ar_id = pawr.pos_ar_id
            )
            UPDATE pos_ar_wsfex_rel pawr
            SET pos_ar_id=qa.pos_ar_id
            FROM qa WHERE qa.wsfex_config_id=pawr.wsfex_config_id
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
