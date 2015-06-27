# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2013 Eynes S.R.L. (http://www.eynes.com.ar) All Rights Reserved.
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
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

from openerp.osv import fields, osv
from openerp.tools.translate import _


class wizard_create_check(osv.osv_memory):
    _name = "wizard.create.check"
    _description = "wizard create check"

    _columns = {
        'bank_account_id': fields.many2one('res.partner.bank', 'Bank', required=True),
        'start_num': fields.char('Start number of check', size=20, required=True),
        'end_num': fields.char('End number of check', size=20, required=True),
        'checkbook_num': fields.char('Checkbook number', size=20, required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id
    }

    def create_checkbook(self, cr, uid, ids, context=None):
        checkbook_obj = self.pool.get('account.checkbook')
        mod_obj = self.pool.get('ir.model.data')
        checkbook_id = False

        if context is None:
            context = {}
        for form in self.browse(cr, uid, ids, context=context):
            start_num = int(form.start_num)
            end_num = int(form.end_num)
            if start_num > end_num:
                raise osv.except_osv(_('Error creating Checkbook'), _("End number cannot be lower than Start number"))

            # Creamos los cheques numerados
            checks = []
            for n in range(start_num, end_num + 1):
                check_vals = {'name': str(n)}
                checks.append((0, 0, check_vals))

            # Creamos la chequera
            checkbook_vals = {
                'name': form.checkbook_num,
                'bank_id': form.bank_account_id.bank.id,
                'bank_account_id': form.bank_account_id.id,
                'check_ids': checks
            }

            checkbook_id = checkbook_obj.create(cr, uid, checkbook_vals, context)

        if not checkbook_id:
            return {'type': 'ir.actions.act_window_close'}

        return {
            'domain': [('id', '=', str(checkbook_id))],
            'name': 'Checkbook',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.checkbook',
            'view_id': False,
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window'
        }

wizard_create_check()
