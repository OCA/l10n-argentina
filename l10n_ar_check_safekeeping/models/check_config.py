# -*- coding: utf-8 -*-
###############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (Julian Corso)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging

from odoo import models, api, fields, _, exceptions
from odoo.exceptions import ValidationError
from datetime import datetime

_logger = logging.getLogger(__name__)


class AccountCheckConfig(models.Model):
    _inherit = 'account.check.config'

    safekept_account_id = fields.Many2one('account.account', 'Safekept Check Account',
            required=True, help="Account for checks in safekeeping")

