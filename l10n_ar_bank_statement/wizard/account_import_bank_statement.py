# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2014 Eynes - Ingeniería del software All Rights Reserved
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

from openerp.osv import osv, fields

class account_import_statement_lines(osv.osv_memory):
    _name = "account.import.statement.lines"
    _description = "Account Import Statement Lines"
    _columns = {
        #~ , domain=[('journal_id','=',journal_id)]
        'lines': fields.many2many('account.bank.statement.line', 'account_bank_statement_line_rel_', 'statement_id', 'line_id', 'Account Bank Statement Lines')
    }

    def import_statement_lines(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        
        statement_obj = self.pool.get('account.bank.statement')
        statement_line_obj = self.pool.get('account.bank.statement.line')

        statement = statement_obj.browse(cr, uid, context['active_id'], context=context)
        
        data =  self.read(cr, uid, ids, context=context)[0]
        line_ids = data['lines']
        
        if not line_ids:
            return {'type': 'ir.actions.act_window_close'}

        lines_to_statement = [(4, lid) for lid in line_ids]

        statement_obj.write(cr, uid, [statement.id], {'line_ids': lines_to_statement})
        return {'type': 'ir.actions.act_window_close'}

account_import_statement_lines()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
