# -*- coding: utf-8 -*-
import psycopg2
import logging

logger = logging.getLogger(__name__)


def _update_columns(cr):
    try:
        logger.info('Set partner_id to perception_tax_line using account.invoice partner')
        q = """
        -- partner_id is no more a related with account.invoice
        -- Set partner_id to perception_tax_line
        WITH q1 AS (
            SELECT ptl.id ptlid, ai.partner_id pid
            FROM perception_tax_line ptl
                JOIN account_invoice ai ON ai.id = ptl.invoice_id)
        UPDATE perception_tax_line ptl SET partner_id=q1.pid
        FROM q1 WHERE q1.ptlid=ptl.id;
        """
        cr.execute(q)
    except psycopg2.ProgrammingError:
        cr.rollback()
    else:
        cr.commit()

    return True


def migrate(cr, installed_version):
    return _update_columns(cr)
