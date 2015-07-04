# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Eynes - Ingeniería del software All Rights Reserved
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#    All Rights Reserved. See AUTHORS for details.
# 
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################
import time
from openerp.osv import osv, fields


class payment_mode_receipt(osv.osv):
    _inherit= 'payment.mode.receipt'
    _columns = {
        'journal_id': fields.many2one('account.journal', 'Cash/Journal', help="The payment mode journal is need for cash register line")
    }
payment_mode_receipt()
