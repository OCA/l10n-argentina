##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

import logging

from odoo import api, SUPERUSER_ID

from . import models  # noqa
from . import wizard  # noqa


_logger = logging.getLogger(__name__)


def _set_default_afip_codes(cr, reg):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _logger.info("Configuring default AFIP Codes for currencies")
    currency_model = env['res.currency']
    currency_model._set_default_afip_codes()

    _logger.info("Configuring default AFIP Codes for taxes")
    tax_model = env['account.tax']
    tax_model._set_default_afip_codes()
    return True
