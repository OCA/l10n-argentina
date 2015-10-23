# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2015 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2015 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
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

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import except_orm, Warning
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class wsfe_massive_sinchronize(models.TransientModel):
    _name = 'wsfe.massive.sinchronize'
    _desc = 'WSFE Massive Sinchronize'

    voucher_type = fields.Many2one('wsfe.voucher_type', 'Voucher Type', required=True)
    pos_id = fields.Many2one('pos.ar', 'POS', required=True)

    def _search_invoice(self, res):
        invoice_model = self.env['account.invoice']

        # TODO: Estamos repitiendo codigo. Limpiar.
        doc_ids = self.env['res.document.type'].search([('afip_code', '=', res['DocTipo'])])
        document_type = doc_ids and doc_ids[0] or False

        document_type = document_type
        document_number = str(res['DocNro'])
        amount_total = res['ImpTotal']
        amount_no_taxed = res['ImpTotConc']
        amount_taxed = res['ImpNeto']
        #amount_tax = res['ImpIVA'] + res['ImpTrib']
        amount_exempt = res['ImpOpEx']

        domain = [
            ('amount_total', '=', amount_total),
            ('partner_id.vat', '=', document_number),
            ('amount_exempt', '=', amount_exempt),
            ('amount_taxed', '=', amount_taxed),
            ('amount_no_taxed', '=', amount_no_taxed),
            ('state', 'in', ('draft','proforma2','proforma'))]

        invoice_ids = invoice_model.search(domain)

        # Si hay mas de una, retorna la primera
        if len(invoice_ids):
            return invoice_ids[0]

        return False

    @api.one
    def sinchronize(self):
        wsfe_conf_model = self.env['wsfe.config']
        invoice_model = self.env['account.invoice']

        conf = wsfe_conf_model.get_config()
        pos = int(self.pos_id.name)
        voucher_type = self.voucher_type.code

        # Obtenemos el ultimo numero de factura
        # FIX: Corregir en el caso que sea una ND
        last_invoice = invoice_model.search([('state', 'in', ('open', 'paid')),
                              ('pos_ar_id', '=', self.pos_id.id),
                              ('type', '=', self.voucher_type.document_type),
                              ('is_debit_note', '=', self.voucher_type.document_type=='out_debit'),
                              ('denomination_id', '=', self.voucher_type.denomination_id.id)],
                              order='internal_number desc', limit=1)

        # Buscamos la desincronizacion
        last_number = int(last_invoice.internal_number.split('-')[1])
        last_wsfe_number = conf.get_last_voucher(pos, voucher_type)

        # Chequeamos si esta todo sincronizado
        if last_number == last_wsfe_number:
            raise Warning(_('All voucher of this type and POS are sinchronized.'))

        cr = self.env.cr
        for number in range(last_number+1, last_wsfe_number+1):
            logger.info("Sincronizando comprobante %d" % number)
            res = conf.get_voucher_info(pos, voucher_type, number)
            logger.debug("Informacion obtenida de AFIP %s" % res)

            # Buscamos una factura que coincida
            invoice = self._search_invoice(res)

            # No se encontro la factura
            if not invoice:
                raise except_orm(_('Voucher Not Found!'),
                    _('Voucher %d of pos %s has not been found.') %
                            (number, self.pos_id.name))

            date_invoice = time.strftime(DEFAULT_SERVER_DATE_FORMAT,
                           time.strptime(str(res['CbteFch']), '%Y%m%d'))
            cae_due_date = time.strftime(DEFAULT_SERVER_DATE_FORMAT,
                           time.strptime(str(res['FchVto']), '%Y%m%d'))
            cae = str(res['CodAutorizacion'])

            invoice.wsfe_relate_invoice(pos, number, date_invoice,
                                        cae, cae_due_date)

            if self.env.context.get('commit', True):
                cr.commit()

        return {'type': 'ir.actions.act_window_close'}
