# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2013 E-MIPS (http://www.e-mips.com.ar) All Rights Reserved.
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
from tools.translate import _
import decimal_precision as dp
import netsvc
import time

class wsfe_sinchronize_voucher(osv.osv_memory):
    """
    This wizard is used to get information about a voucher informed to AFIP through WSFE
    """
    _name = "wsfe.sinchronize.voucher"
    _description = "WSFE Sinchroniza Voucher"

    _columns = {
        'voucher_type': fields.many2one('wsfe.voucher_type', 'Voucher Type', required=True),
        'pos_id': fields.many2one('pos.ar', 'POS', required=True),
        'voucher_number': fields.integer('Number', required=True),

        'document_type': fields.many2one('res.document.type', 'Document Type', readonly=True),
        'document_number': fields.integer('Document Number', readonly=True),
        'date_invoice': fields.date('Date Invoice', readonly=False),
        'amount_total': fields.float(digits_compute=dp.get_precision('Account'), string="Total", readonly=True),
        'amount_no_taxed': fields.float(digits_compute=dp.get_precision('Account'), string="No Taxed", readonly=True),
        #'amount_untaxed': fields.float(digits_compute=dp.get_precision('Account'), string="Untaxed", readonly=True),
        'amount_taxed': fields.float(digits_compute=dp.get_precision('Account'), string="Taxed", readonly=True),
        'amount_tax': fields.float(digits_compute=dp.get_precision('Account'), string="Tax", readonly=True),
        'amount_exempt': fields.float(digits_compute=dp.get_precision('Account'), string="Amount Exempt", readonly=True),
        #'currency': fields.many2one('res.currency', string="Currency", readonly=True),
        'cae': fields.char('CAE', size=32, required=False, readonly=True),
        'cae_due_date': fields.date('CAE Due Date', readonly=False),
        'date_process': fields.datetime('Date Processed', readonly=False),

        'infook': fields.boolean('Info OK'),
        'invoice_id': fields.many2one('account.invoice', 'Invoice'),
    }

    _defaults = {
        'infook': lambda *a: False,
        }

    def get_voucher_info(self, cr, uid, ids, context=None):
        wsfe_conf_obj = self.pool.get('wsfe.config')

        # Obtenemos los datos puestos por el usuario
        data = self.browse(cr, uid, ids[0], context=context)

        conf = wsfe_conf_obj.get_config(cr, uid)
        voucher_type = int(data.voucher_type.code)
        pos = int(data.pos_id.name)
        number = data.voucher_number

        res = wsfe_conf_obj.get_voucher_info(cr, uid, [conf.id], pos, voucher_type, number, context=context)

        doc_ids = self.pool.get('res.document.type').search(cr, uid, [('afip_code', '=', str(res['DocTipo']))])
        document_type = doc_ids and doc_ids[0] or False

        di = time.strptime(str(res['CbteFch']), '%Y%m%d')
        dd = time.strptime(str(res['FchVto']), '%Y%m%d')
        dpr = time.strptime(str(res['FchProceso']), '%Y%m%d%H%M%S')

        # TODO: Tandriamos que filtrar las invoices por Tipo de Comprobante tambien
        # para ello podemos agregar un par de campos mas para usarlos como filtros,
        # por ejemplo, is_debit_note y type
        vals = {
            'document_type': document_type,
            'document_number': res['DocNro'],
            'date_invoice': di,#str(res['CbteFch']),
            'amount_total': res['ImpTotal'],
            'amount_no_taxed':res['ImpTotConc'],
            #'amount_untaxed':res['ImpNeto'],
            'amount_taxed':res['ImpNeto'],
            'amount_tax':res['ImpIVA'] + res['ImpTrib'],
            'amount_exempt':res['ImpOpEx'],
            #'currency':,
            'cae':res['CodAutorizacion'],
            'cae_due_date': dd,
            'date_process': dpr,
            'infook': True,
        }

        self.write(cr, uid, ids, vals)
        return True

    def relate_invoice(self, cr, uid, ids, context=None):
        wsfe_conf_obj = self.pool.get('wsfe.config')
        inv_obj = self.pool.get('account.invoice')
        conf = wsfe_conf_obj.get_config(cr, uid)
        wf_service = netsvc.LocalService('workflow')

        # Obtenemos los datos puestos por el usuario
        data = self.browse(cr, uid, ids[0], context=context)
        inv = data.invoice_id

        # Hacemos un par de chequeos, por las dudas
        electronic_pos_ids = [p.id for p in conf.point_of_sale_ids]
        if inv.pos_ar_id.id not in electronic_pos_ids:
            raise osv.except_osv(_("WSFE Error"), _("This invoice does not belongs to an electronic point of sale"))

        # Tomamos las facturas y mandamos a realizar los asientos contables primero.
        inv_obj.action_move_create(cr, uid, [inv.id], context)

        # Reload info...
        inv = inv_obj.browse(cr, uid, inv.id, context)

        move_id = inv.move_id and inv.move_id.id or False
        self.pool.get('account.move').post(cr, uid, [move_id], context={'invoice':inv})

        # TODO: Agregar el date_invoice para que sea el de la AFIP
        invoice_vals = {
            'internal_number': '%04d-%08d' % (int(data.pos_id.name), data.voucher_number),
            'cae': data.cae,
            'cae_due_date': data.cae_due_date,
        }

        inv_obj.write(cr, uid, inv.id, invoice_vals)

        reference = inv.reference or ''
        if not reference:
            invoice_name = inv_obj.name_get(cr, uid, [inv.id])[0][1]
            ref = invoice_name
        else:
            ref = reference

        inv_obj._update_reference(cr, uid, inv, ref, context)

        # Llamamos al workflow para que siga su curso
        wf_service.trg_validate(uid, 'account.invoice', inv.id, 'invoice_massive_open', cr)

        return {'type': 'ir.actions.act_window_close'}

wsfe_sinchronize_voucher()
