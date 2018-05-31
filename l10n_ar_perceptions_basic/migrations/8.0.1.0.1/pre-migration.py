# -*- coding: utf-8 -*-
import psycopg2
import logging

logger = logging.getLogger(__name__)


def _do_update(cr, installed_version):
    try:
        q = """
            DELETE FROM ir_model_data
            WHERE module ~ 'l10n_ar_perceptions_basic'
            AND model IN (
                'account.tax',
                'account.tax.code',
                'perception.perception',
                'account.account'
            );
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
