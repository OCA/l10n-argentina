# -*- coding: utf-8 -*-
###############################################################################
#   Copyright (c) 2018 Eynes/E-Mips (Julian Corso)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging

from openerp import models, fields, api  # , api, fields, _, exceptions
# from openerp.exceptions import except_orm
# from openerp.addons.decimal_precision import decimal_precision as dp
# from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, \
#       DEFAULT_SERVER_DATETIME_FORMAT, float_compare


_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.multi
    def get_pbc_ids(self):
        """
        Get PosBoxConcepts that are asociated with this user.
        """
        self.ensure_one()
        pbc_lst = self.env['pos.box.concept'].search([]).ids
        allowed_pbc = self.env['pos.box.concept.allowed'].search([])
        for apbc in allowed_pbc:
            if self.id in apbc.user_ids.ids:
                pbc_lst = apbc.concept_ids.ids
        return pbc_lst
