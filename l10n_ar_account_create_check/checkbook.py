# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2009 Zikzakmedia S.L. (http://zikzakmedia.com) All Rights Reserved.
#                       Jordi Esteve <jesteve@zikzakmedia.com>
#    $Id$
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

from osv import osv, fields

class account_checkbook(osv.osv):
    _name = "account.checkbook"
    _description = "Checkbook"

    _columns = {
        'name': fields.char('Checkbook Number', size=32, required=True),
        'bank_id': fields.many2one('res.bank','Bank', required=True),
        'bank_account_id': fields.many2one('res.partner.bank','Bank', required=True),
        'check_ids': fields.one2many('account.checkbook.check', 'checkbook_id', 'Available Checks',
                                     domain="[('state','=','draft')]", readonly=True),
        'issued_check_ids': fields.one2many('account.issued.check', 'checkbook_id', 'Issued Checks', readonly=True),
    }

account_checkbook()

class checkbook_check(osv.osv):
    """Relacion entre Chequera y cheques por nro de cheque"""
    _name = "account.checkbook.check"
    _description = "Checkbook Check"

    _columns = {
        'name': fields.char('Check Number', size=20, required=True),
        'checkbook_id': fields.many2one('account.checkbook', 'Checkbook number', required=True),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('done', 'Used')
            ], 'State', readonly=True),
    }

    _defaults = {
		'state': 'draft'
    }
checkbook_check()



class checkbook(osv.osv):
    _name = "checkbook"
    _description = "checkbook"

    _columns = {
        'bank_id': fields.many2one('res.partner.bank','Bank', required=True),
        'name': fields.char('Number of check', size=20, required=True),
        'checkbook_num': fields.char('Checkbook number', size=20, required=True),
        'state': fields.char('State', size=40, required=True),
    }
    
    _defaults = {
		'state': 'draft'
    }
checkbook()


class account_issued_check(osv.osv):
    _inherit = 'account.issued.check'

    _columns = {
        'check_id': fields.many2one('checkbook', 'Check'),
        'checkbook_id': fields.many2one('account.checkbook', 'Checkbook'),
        'number': fields.char('Check Number', size=20),
        }
        
    def on_change_check_id(self, cr, uid, ids, check_id, context=None):
        if context is None:
            context = {}
        if not check_id:
            return {'value':{}}

        check = self.pool.get('checkbook').browse(cr, uid, check_id, context=context)
        return {'value':{'account_bank_id': check.bank_id.id, 'bank_id': check.bank_id.bank.id, 'number': check.name}}
        
    def write(self, cr, uid, ids, vals, context=None):
		a = vals.get('check_id', False)
		if a:
			sql = 'select check_id from account_issued_check where id = ' + str(ids[0])
			cr.execute(sql)
			aux_check_id = cr.fetchone()
			self.pool.get('checkbook').write(cr, uid, aux_check_id, {'state': 'draft'})
			self.pool.get('checkbook').write(cr, uid, a, {'state': 'done'})
		return super(account_issued_check, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context=None):
		a = vals.get('check_id', False)
		if a:
			self.pool.get('checkbook').write(cr, uid, a, {'state': 'done'})
		return super(account_issued_check, self).create(cr, uid, vals, context=context)
		
    def unlink(self, cr, uid, ids, context=None):
		sql = 'select check_id from account_issued_check where id = ' + str(ids[0])
		cr.execute(sql)
		aux_check_id = cr.fetchone()
		self.pool.get('checkbook').write(cr, uid, aux_check_id, {'state': 'draft'})
		return super(account_issued_check, self).unlink(cr, uid, ids, context=context)
        
account_issued_check()
