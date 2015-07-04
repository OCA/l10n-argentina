# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2010-2014 Eynes - Ingeniería del software All Rights Reserved
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#    All Rights Reserved. See AUTHORS for details.
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

class CashBox(osv.osv_memory):
    _register = False
    _inherit = 'CashBox'
    _columns = {
        'statement_line_type_id' : fields.many2one('cash.statement.line.type', 'Type', required=True),
        #~ 'employee_id': fields.many2one('hr.employee', 'Employee'),
        'voucher': fields.char('Voucher', size=40),
    }

    def _run(self, cr, uid, ids, records, context=None):
        for box in self.browse(cr, uid, ids, context=context):
            for record in records:
                self._create_bank_statement_line(cr, uid, box, record, context=context)

        return {}

class CashBoxIn(CashBox):
    _name = 'cash.box.in'
    _inherit = 'cash.box.in'
    _columns = {
        'statement_line_type_id' : fields.many2one('cash.statement.line.type', 'Type', required=True),
        #~ 'employee_id': fields.many2one('hr.employee', 'Employee'),
        'voucher': fields.char('Voucher', size=40),
    }

    def onchange_statement_type(self, cr, uid, ids, statement_type_id, context=None):
        if not statement_type_id:
            return {'name': ''}
            
        aux = self.pool.get('cash.statement.line.type').browse(cr, uid, statement_type_id, context=None)
        if aux:
            return {'value':{'name': aux.name}}

    def _compute_values_for_statement_line(self, cr, uid, box, record, context=None):
        return {
            'statement_id' : record.id,
            'journal_id' : record.journal_id.id,
            #~ 'account_id' : record.journal_id.internal_account_id.id,
            'account_id' : box.statement_line_type_id.account_id.id,
            'amount' : box.amount or 0.0,
            'ref' : '%s' % (box.ref or ''),
            'name' : box.statement_line_type_id.name,
            'type': 'income',
            'state': 'conciliated',
            'ref': box.voucher,
            'creation_type': 'manual',
        }

CashBoxIn()

class CashBoxOut(CashBox):
    _name = 'cash.box.out'
    _inherit = 'cash.box.out'
    _columns = {
        'statement_line_type_id' : fields.many2one('cash.statement.line.type', 'Type', required=True),
        #~ 'employee_id': fields.many2one('hr.employee', 'Employee'),
        'voucher': fields.char('Voucher', size=40),
    }

    def onchange_statement_type(self, cr, uid, ids, statement_type_id, context=None):
        if not statement_type_id:
            return {'name': ''}
            
        aux = self.pool.get('cash.statement.line.type').browse(cr, uid, statement_type_id, context=None)
        if aux:
            return {'value':{'name': aux.name}}

    def _compute_values_for_statement_line(self, cr, uid, box, record, context=None):
        amount = box.amount or 0.0
        return {
            'statement_id' : record.id,
            'journal_id' : record.journal_id.id,
            #~ 'account_id' : record.journal_id.internal_account_id.id,
            'account_id' : box.statement_line_type_id.account_id.id,
            'amount' : -amount if amount > 0.0 else amount,
            #~ 'name' : box.name,
            'name' : box.statement_line_type_id.name,
            'type': 'expenses',
            'state': 'conciliated',
            'ref': box.voucher,
            'creation_type': 'manual',
        }

CashBoxOut()
