##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

import logging

from odoo import SUPERUSER_ID
from odoo import api

_logger = logging.getLogger(__name__)


def do_migrate(cr):
    q = """
    SELECT
        ru.id, ru.default_pos, rcur.cid
    FROM res_users ru
        JOIN res_company_users_rel rcur
            ON rcur.user_id = ru.id
    WHERE ru.default_pos IS NOT NULL;
    """
    cr.execute(q)
    todo = cr.fetchall()
    env = api.Environment(cr, SUPERUSER_ID, {})
    users_model = env['res.users']
    for user_id, pos_id, company_id in todo:
        user = users_model.with_context(
            force_company=company_id).browse(user_id)
        user.property_default_pos_id = pos_id
        _logger.info('%s with company %s default_pos -> %s' %
                     (user, company_id, pos_id))


def migrate(cr, version):
    do_migrate(cr)
