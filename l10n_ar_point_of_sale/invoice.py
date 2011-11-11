# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2008-2011
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
from osv import osv, fields


class invoice(osv.osv):
    _name = "account.invoice"
    _inherit = "account.invoice"
    _description = ""
    _columns = {
        'type': fields.selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Supplier Invoice'),
            ('out_refund','Customer Refund'),
            ('in_refund','Supplier Refund'),
            ('out_debit','Customer Debit'),
            ('in_debit','Supplier Debit'),
            ],'Type', readonly=True, select=True, change_default=True),
        'pos_ar_id' : fields.many2one('pos.ar','Point of Sale'),
        'denomination_id' : fields.many2one('invoice.denomination','Denomination', readonly=True),
        'internal_number': fields.char('Invoice Number', size=32, readonly=False, help="Unique number of the invoice, computed automatically when the invoice is created."),
    }
    
    def action_number(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        #TODO: not correct fix but required a frech values before reading it.
        self.write(cr, uid, ids, {})

        for obj_inv in self.browse(cr, uid, ids, context=context):
            id = obj_inv.id
            invtype = obj_inv.type
            number = obj_inv.number
            move_id = obj_inv.move_id and obj_inv.move_id.id or False
            reference = obj_inv.reference or ''
            
#del        self.write(cr, uid, ids, {'internal_number':number})
#add:         
        #~ si el usuario no ingreso un numero, busco el ultimo y lo incremento , si no hay ultimo va 1. 
        #~ si el usuario hizo un ingreso dejo ese numero
            if not obj_inv.internal_number:
                pos_ar = obj_inv.pos_ar_id.id
                cr.execute("select max(to_number(internal_number, '99999999')) from account_invoice where internal_number ~ '^[0-9]+$' and pos_ar_id=%s and state in %s", (pos_ar, ('open', 'paid', 'cancel',)))
                max_number = cr.fetchone()    
                if not max_number[0]:
                    val = '%08d' % 1
                    self.write(cr, uid, id, {'internal_number' : val })
                else :
                    val = '%08d' % ( int(max_number[0]) + 1)
                    self.write(cr, uid, id, {'internal_number' : val })
            else :
                self.write(cr, uid, id, {'internal_number' : ('%08d' % int(obj_inv.internal_number))})
#end add            
            if invtype in ('in_invoice', 'in_refund'):
                if not reference:
                    ref = self._convert_ref(cr, uid, number)
                else:
                    ref = reference
            else:
                ref = self._convert_ref(cr, uid, number)

            cr.execute('UPDATE account_move SET ref=%s ' \
                    'WHERE id=%s AND (ref is null OR ref = \'\')',
                    (ref, move_id))
            cr.execute('UPDATE account_move_line SET ref=%s ' \
                    'WHERE move_id=%s AND (ref is null OR ref = \'\')',
                    (ref, move_id))
            cr.execute('UPDATE account_analytic_line SET ref=%s ' \
                    'FROM account_move_line ' \
                    'WHERE account_move_line.move_id = %s ' \
                        'AND account_analytic_line.move_id = account_move_line.id',
                        (ref, move_id))

            for inv_id, name in self.name_get(cr, uid, [id]):
                ctx = context.copy()
                if obj_inv.type in ('out_invoice', 'out_refund'):
                    ctx = self.get_log_context(cr, uid, context=ctx)
                message = ('Invoice ') + " '" + name + "' "+ ("is validated.")
                self.log(cr, uid, inv_id, message, context=ctx)
        return True
        
    
    def write(self, cr, uid, ids, vals, context=None):
        
        if 'internal_number' in vals.keys():
            try: 
                int(vals['internal_number']) 
            except :
                raise osv.except_osv( ('Error'),
                                      ('The Invoice Number can not contain characters'))
        return super(invoice, self).write(cr, uid, ids, vals, context=context)
    
    def refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None):
    
        #devuelve los ids de las invoice modificadas
        inv_ids = super(invoice , self).refund(cr, uid, ids, date=None, period_id=None, description=None, journal_id=None)
        #busco los puntos de venta de las invoices anteriores
        #TODO falta iterar sobre las facturas creadas inv_ids
        res=[]
        inv_obj = self.browse(cr, uid , ids , context=None)
        for obj in inv_obj:
            self.write(cr, uid , inv_ids , {'pos_ar_id': obj.pos_ar_id.id } , context=None)
             
        return inv_ids
        
invoice()
