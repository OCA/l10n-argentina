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
from tools.translate import _

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
        'denomination_id' : fields.many2one('invoice.denomination','Denomination'),
        'internal_number': fields.char('Invoice Number', size=32, help="Unique number of the invoice, computed automatically when the invoice is created."),
    }
    
    def action_number(self, cr, uid, ids, context=None):
        pos_ar_obj = self.pool.get('pos.ar')
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
            internal_number = False
            pos_ar = obj_inv.pos_ar_id.id
            pos_ar_name = False
            if pos_ar:
                pos_ar_name = pos_ar_obj.name_get(cr, uid, [pos_ar])[0][1]
            
            if not obj_inv.internal_number:
                cr.execute("select max(to_number(internal_number, '99999999')) from account_invoice where internal_number ~ '^[0-9]+$' and pos_ar_id=%s and state in %s and type='out_invoice'", (pos_ar, ('open', 'paid', 'cancel',)))
                max_number = cr.fetchone()    
                if not max_number[0]:
                    internal_number = '%08d' % 1
                    self.write(cr, uid, id, {'internal_number' : internal_number })
                else :
                    internal_number = '%08d' % ( int(max_number[0]) + 1)
                    self.write(cr, uid, id, {'internal_number' : internal_number })
            else :
                internal_number = ('%08d' % int(obj_inv.internal_number))
                self.write(cr, uid, id, {'internal_number' : internal_number})
#end add            
            if invtype in ('in_invoice', 'in_refund'):
                if not reference:
#mod                #self._convert_ref(cr, uid, internal_number)   
                    ref = internal_number 
                else:
                    ref = reference
            else:
#mod            #ref = self._convert_ref(cr, uid, number)
                ref = pos_ar_name + ' ' + internal_number

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
                message = _('Invoice ') + " '" + name + "' "+ _("is validated.")
                self.log(cr, uid, inv_id, message, context=ctx)
        return True
        
    
    def write(self, cr, uid, ids, vals, context=None):
        
        if 'internal_number' in vals.keys():
            try: 
                int(vals['internal_number']) 
            except :
                raise osv.except_osv( _('Error'),
                                      _('The Invoice Number can not contain characters'))
        return super(invoice, self).write(cr, uid, ids, vals, context=context)
    
    def refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None):
    
        #devuelve los ids de las invoice modificadas
        inv_ids = super(invoice , self).refund(cr, uid, ids, date=None, period_id=None, description=None, journal_id=None)
        #busco los puntos de venta de las invoices anteriores

        inv_obj = self.browse(cr, uid , ids , context=None)
        for obj in inv_obj:
            self.write(cr, uid , inv_ids , {'pos_ar_id': obj.pos_ar_id.id } , context=None)
             
        return inv_ids
    
    def onchange_partner_id(self, cr, uid, ids, type, partner_id,\
            date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False , context=None):
        res =   super(invoice, self).onchange_partner_id(cr, uid, ids, type, partner_id,\
                date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False)
        fiscal_position_id = res['value']['fiscal_position']
        if not fiscal_position_id:
            return res
        
        fiscal_pool = self.pool.get('account.fiscal.position')
        pos_pool = self.pool.get('pos.ar')
        denomination_id = fiscal_pool.browse(cr, uid , fiscal_position_id).denomination_id.id
        res.update({'domain': {'pos_ar_id': [('denomination_id', '=', denomination_id)]}})
        #para las invoices de suppliers
        denom_sup_id = fiscal_pool.browse(cr, uid , fiscal_position_id).denom_supplier_id.id
        res['value'].update({'denomination_id': denom_sup_id})
        #para las customers invoices
        pos = pos_pool.search( cr, uid , [('denomination_id','=',denomination_id)] , limit=1 )
        res['value'].update({'pos_ar_id': pos[0]})
        
        return res
        
    def invoice_pay_customer(self, cr, uid, ids, context=None):
        if not ids: return []
        inv = self.browse(cr, uid, ids[0], context=context)
        res = super(invoice, self).invoice_pay_customer(cr, uid, ids, context=context)
        res['context']['type'] = inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'
        
        return res
        
        
invoice()
