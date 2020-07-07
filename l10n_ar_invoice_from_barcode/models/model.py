# -*- coding: utf-8 -*-
###############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (Julian Corso)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging

from openerp import models  # , api, fields, _, exceptions
# from openerp.exceptions import except_orm
# from openerp.addons.decimal_precision import decimal_precision as dp
# from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, \
#       DEFAULT_SERVER_DATETIME_FORMAT, float_compare


_logger = logging.getLogger(__name__)


class Model(models.Model):
    _name = 'model'
