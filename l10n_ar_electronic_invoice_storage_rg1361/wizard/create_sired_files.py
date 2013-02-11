# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-2013 E-MIPS Electronica e Informatica
#               All Rights Reserved (<http://www.e-mips.com.ar>).
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

from osv import osv, fields
from tools.translate import _

class create_sired_files(osv.osv_memory):
    _name = 'create.sired.files'
    _description = 'Wizard Create Sired Files'

    _columns = {
        'period_id': fields.many2one('account.period', 'Period'),
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}

        res = super(create_sired_files, self).default_get(cr, uid, fields, context=context)

        if context.get('active_model') == 'account.period':
            res['period_id'] = context.get('active_id', False)

        return res

    def _generate_head_file(self, cr, uid, invoice_ids, context):
        pass

    def create_files(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        data = self.browse(cr, uid, ids, context)[0]

        period = data.period

        # Buscamos las facturas del periodo pedido
        invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('period_id','=',period.id)], context=context)
        
        self._generate_head_file(cr, uid, invoice_ids, context)

        return {'type': 'ir.actions.act_window_close'}

create_sired_files()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
