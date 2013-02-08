# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2013 Eynes S.R.L. (http://www.eynes.com.ar) All Rights Reserved.
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

from osv import fields, osv
from tools.translate import _
import string

class wizard_create_check(osv.osv_memory):
    _name = "wizard.create.check"
    _description = "wizard create check"

    _columns = {
        'bank_id': fields.many2one('res.partner.bank','Bank'),
        'start_num': fields.char('Start number of check',size=20),
        'end_num': fields.char('End number of check',size=20),
        'checkbook_num': fields.char('Checkbook number',size=20),
    }

    def create_checkbook(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for form in self.browse(cr, uid, ids, context=context):
			min = int(form.start_num)
			max = int(form.end_num)
			print min
			print max
			if min < max:
				for n in range(min, max+1):
					print n
					id_prestacion = self.pool.get('checkbook').create(cr, uid, {
						'name': str(n),
						'bank_id': form.bank_id.id,
						'checkbook_num': form.checkbook_num
						})
			else:
				su='El numero final de la chequera debe ser mayor al inicial'
				raise osv.except_osv(('Error 701'),(su))
        
        return { 'type': 'ir.actions.act_window_close' }


wizard_create_check()
