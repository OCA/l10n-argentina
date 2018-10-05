###############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (Cardozo Nicolás Joaquin)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging
from odoo.addons import decimal_precision as dp
from odoo import models, fields, api, _  # , api, fields, _, exceptions
from odoo.exceptions import RedirectWarning, ValidationError, UserError
from odoo.tools import float_compare
# from odoo.addons.decimal_precision import decimal_precision as dp
# from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, \
#         DEFAULT_SERVER_DATETIME_FORMAT, float_compare


_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    # TODO
    @api.multi
    def action_pay_invoices(self):
        pass
