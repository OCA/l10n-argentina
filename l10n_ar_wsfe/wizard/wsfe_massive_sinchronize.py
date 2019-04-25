###############################################################################
#   Copyright (c) 2012-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from odoo import models, fields, api, _
import time
from odoo.exceptions import UserError, Warning
import logging

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

logger = logging.getLogger(__name__)


class wsfe_massive_sinchronize(models.TransientModel):
    _name = 'wsfe.massive.sinchronize'
    _desc = 'WSFE Massive Sinchronize'

    voucher_type = fields.Many2one('wsfe.voucher_type', 'Voucher Type',
                                   required=True)
    pos_id = fields.Many2one('pos.ar', 'POS', required=True)

    def _search_invoice(self, res):
        invoice_model = self.env['account.invoice']

        # TODO: Estamos repitiendo codigo. Limpiar.
        doc_ids = self.env['res.document.type'].search(
            [('afip_code', '=', res['DocTipo'])])
        document_type = doc_ids and doc_ids[0] or False

        document_type = document_type
        document_number = [str(res['DocNro'])] if res['DocNro'] \
            else [str(res['DocNro']), '', False]
        amount_total = res['ImpTotal']
        amount_no_taxed = res['ImpTotConc']
        amount_taxed = res['ImpNeto']
        # amount_tax = res['ImpIVA'] + res['ImpTrib']
        amount_exempt = res['ImpOpEx']

        domain = [
            ('amount_total', '=', amount_total),
            ('amount_exempt', '=', amount_exempt),
            ('amount_taxed', '=', amount_taxed),
            ('amount_no_taxed', '=', amount_no_taxed),
            ('state', 'in', ('draft', 'proforma2', 'proforma'))]

        if document_type and document_type.afip_code != '99':
            domain.append(('partner_id.vat', 'in', document_number))

        invoices = invoice_model.search(domain)

        if len(invoices) == 1:
            return invoices
        # Si hay mas de una, retorna la primera que tenga wsfe_request
        if len(invoices) > 1:
            final_inv = invoices.filtered(lambda x: x.wsfe_request_ids)
            if final_inv:
                return final_inv[0]
        return False

    @api.multi
    def sinchronize(self):
        self.ensure_one()
        wsfe_conf_model = self.env['wsfe.config']
        invoice_model = self.env['account.invoice']

        conf = wsfe_conf_model.get_config()
        pos = int(self.pos_id.name)
        voucher_type = self.voucher_type.code

        # Obtenemos el ultimo numero de factura
        # FIX: Corregir en el caso que sea una ND
        last_invoice = invoice_model.search([
            ('state', 'in', ('open', 'paid')),
            ('pos_ar_id', '=', self.pos_id.id),
            ('type', '=', self.voucher_type.document_type),
            ('is_debit_note', '=',
             self.voucher_type.document_type == 'out_debit'),
            ('denomination_id', '=', self.voucher_type.denomination_id.id)],
            order='internal_number desc', limit=1)

        # Buscamos la desincronizacion
        last_number = int(last_invoice.internal_number.split('-')[1])
        last_wsfe_number = conf.get_last_voucher(pos, voucher_type)

        # Chequeamos si esta todo sincronizado
        if last_number == last_wsfe_number:
            raise Warning(
                _('All voucher of this type and POS are sinchronized.'))

        cr = self.env.cr
        invoices = self.env['account.invoice']
        for number in range(last_number+1, last_wsfe_number+1):
            logger.info("Sincronizando comprobante %d" % number)
            res = conf.get_voucher_info(pos, voucher_type, number)
            logger.debug("Informacion obtenida de AFIP %s" % res)

            # Buscamos una factura que coincida
            invoice = self._search_invoice(res)

            # No se encontro la factura
            if not invoice:
                raise UserError(
                    _('Voucher Not Found!\n') +
                    _('Voucher %d of pos %s has not been found.') %
                    (number, self.pos_id.name))

            invoices += invoice

            date_invoice = time.strftime(
                DEFAULT_SERVER_DATE_FORMAT,
                time.strptime(str(res['CbteFch']), '%Y%m%d'))
            cae_due_date = time.strftime(
                DEFAULT_SERVER_DATE_FORMAT,
                time.strptime(str(res['FchVto']), '%Y%m%d'))
            cae = str(res['CodAutorizacion'])

            invoice.wsfe_relate_invoice(pos, number, date_invoice,
                                        cae, cae_due_date)

            if self.env.context.get('commit', True):
                cr.commit()

        if invoices:
            act_window = {
                'name': _('Updated Invoices'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.invoice',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'target': 'current',
                'domain': [('id', 'in', invoices.ids)],
            }
            return act_window
        else:
            return {'type': 'ir.actions.act_window_close'}
