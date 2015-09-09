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
from openerp import api
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.addons import decimal_precision as dp
from openerp import netsvc
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


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
        'document_number': fields.char('Document Number', readonly=True),
        'date_invoice': fields.date('Date Invoice', readonly=True),
        'amount_total': fields.float(digits_compute=dp.get_precision('Account'), string="Total", readonly=True),
        'amount_no_taxed': fields.float(digits_compute=dp.get_precision('Account'), string="No Taxed", readonly=True),
        #'amount_untaxed': fields.float(digits_compute=dp.get_precision('Account'), string="Untaxed", readonly=True),
        'amount_taxed': fields.float(digits_compute=dp.get_precision('Account'), string="Taxed", readonly=True),
        'amount_tax': fields.float(digits_compute=dp.get_precision('Account'), string="Tax", readonly=True),
        'amount_exempt': fields.float(digits_compute=dp.get_precision('Account'), string="Amount Exempt", readonly=True),
        #'currency': fields.many2one('res.currency', string="Currency", readonly=True),
        'cae': fields.char('CAE', size=32, required=False, readonly=True),
        'cae_due_date': fields.date('CAE Due Date', readonly=True),
        'date_process': fields.datetime('Date Processed', readonly=True),

        'infook': fields.boolean('Info OK'),
        'invoice_id': fields.many2one('account.invoice', 'Invoice'),
    }

    _defaults = {
        'infook': lambda *a: False,
    }

    @api.v7
    def onchange_voucher(self, cr, uid, ids, voucher_type, pos_id, voucher_number, context=None):

        if not context:
            context = {}

        if not voucher_type or not pos_id or not voucher_number:
            return {}

        wsfe_conf_obj = self.pool.get('wsfe.config')
        voucher_type_obj = self.pool.get('wsfe.voucher_type')
        pos_obj = self.pool.get('pos.ar')

        conf = wsfe_conf_obj.get_config(cr, uid)
        reads = voucher_type_obj.read(cr, uid, voucher_type, ['code'], context=context)['code']
        if reads:
            voucher_type = int(reads)

        reads = pos_obj.read(cr, uid, pos_id, ['name'], context=context)['name']
        if reads:
            pos = int(reads)

        number = voucher_number

        res = wsfe_conf_obj.get_voucher_info(cr, uid, [conf.id], pos, voucher_type, number, context=context)

        doc_ids = self.pool.get('res.document.type').search(cr, uid, [('afip_code', '=', str(res['DocTipo']))])
        document_type = doc_ids and doc_ids[0] or False

        di = time.strftime(DEFAULT_SERVER_DATE_FORMAT, time.strptime(str(res['CbteFch']), '%Y%m%d'))
        dd = time.strftime(DEFAULT_SERVER_DATE_FORMAT, time.strptime(str(res['FchVto']), '%Y%m%d'))
        dpr = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, time.strptime(str(res['FchProceso']), '%Y%m%d%H%M%S'))

        # TODO: Tandriamos que filtrar las invoices por Tipo de Comprobante tambien
        # para ello podemos agregar un par de campos mas para usarlos como filtros,
        # por ejemplo, is_debit_note y type
        vals = {
            'document_type': document_type,
            'document_number': str(res['DocNro']),
            'date_invoice': di,  # str(res['CbteFch']),
            'amount_total': res['ImpTotal'],
            'amount_no_taxed': res['ImpTotConc'],
            #'amount_untaxed':res['ImpNeto'],
            'amount_taxed': res['ImpNeto'],
            'amount_tax': res['ImpIVA'] + res['ImpTrib'],
            'amount_exempt': res['ImpOpEx'],
            #'currency':,
            'cae': str(res['CodAutorizacion']),
            'cae_due_date': dd,
            'date_process': dpr,
            'infook': True,
        }

        return {'value': vals}

    def relate_invoice(self, cr, uid, ids, context=None):
        wsfe_conf_obj = self.pool.get('wsfe.config')
        inv_obj = self.pool.get('account.invoice')
        conf = wsfe_conf_obj.get_config(cr, uid)
        wf_service = netsvc.LocalService('workflow')

        # Obtenemos los datos puestos por el usuario
        data = self.browse(cr, uid, ids[0], context=context)
        inv = data.invoice_id

        if not data.infook:
            raise osv.except_osv(_("WSFE Error"), _("Sinchronize process is not correct!"))

        # Hacemos un par de chequeos, por las dudas
        electronic_pos_ids = [p.id for p in conf.point_of_sale_ids]
        if inv.pos_ar_id.id not in electronic_pos_ids:
            raise osv.except_osv(_("WSFE Error"), _("This invoice does not belongs to an electronic point of sale"))

        # Tomamos las facturas y mandamos a realizar los asientos contables primero.
        inv_obj.action_move_create(cr, uid, [inv.id], context)

        # Reload info...
        inv = inv_obj.browse(cr, uid, inv.id, context)

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

        inv._update_reference(ref)

        # Llamamos al workflow para que siga su curso
        wf_service.trg_validate(uid, 'account.invoice', inv.id, 'invoice_massive_open', cr)

        return {'type': 'ir.actions.act_window_close'}

wsfe_sinchronize_voucher()
