# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2017 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2017 Eynes (http://www.eynes.com.ar)
#    All Rights Reserved. See AUTHORS for details.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)


class account_config_settings(osv.osv_memory):
    _inherit = 'account.config.settings'

    _columns = {
        'group_disable_auto_impute_receipts': fields.boolean(
            'Disable autoimpute voucher lines in receipts',
            implied_group='l10n_ar_account_payment.'
            'group_disable_auto_impute_receipts',
            help="Disable auto imputation on receipt voucher "
            "lines when loading a Customer Payment."),
        'group_disable_auto_impute_payments': fields.boolean(
            'Disable autoimpute voucher lines in payments',
            implied_group='l10n_ar_account_payment.'
            'group_disable_auto_impute_payments',
            help="Disable auto imputation on payment voucher "
            "lines when loading a Supplier Payment.")
    }
