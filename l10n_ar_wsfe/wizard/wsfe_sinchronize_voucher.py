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

import time

from dateutil.parser import parse
from openerp import _, api, fields, models
from openerp.addons import decimal_precision as dp
from openerp.exceptions import except_orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


class wsfe_sinchronize_voucher(models.TransientModel):

    """
    This wizard is used to get information about a voucher informed to AFIP through WSFE
    """
    _name = "wsfe.sinchronize.voucher"
    _description = "WSFE Sinchroniza Voucher"

    @api.returns("account.invoice")
    def get_default_invoice_id(self):
        return self.env.context.get('active_id')

    def _get_def_config(self):
        wsfe_conf_model = self.env['wsfe.config']
        return wsfe_conf_model.get_config()

    voucher_type = fields.Many2one('wsfe.voucher_type', 'Voucher Type', required=True)
    pos_id = fields.Many2one('pos.ar', 'POS', required=True)
    invoice_id = fields.Many2one('account.invoice', 'Invoice',
                                 default=lambda w: w.get_default_invoice_id())
    config_id = fields.Reference(string='Config',
                                 selection=[('wsfe.config', 'WSFE'), ('wsfex.config', 'WSFEX')],
                                 size=512)
    voucher_number = fields.Integer('Number', required=True)
    document_type = fields.Many2one('res.document.type', 'Document Type', readonly=True)
    document_number = fields.Char('Document Number', readonly=True)
    date_invoice = fields.Date('Date Invoice', readonly=False)
    amount_total = fields.Float(digits=dp.get_precision('Account'), string="Total", readonly=True)
    amount_no_taxed = fields.Float(digits=dp.get_precision('Account'), string="No Taxed", readonly=True)
    #amount_untaxed = fields.float(digits=dp.get_precision('Account'), string="Untaxed", readonly=True)
    amount_taxed = fields.Float(digits=dp.get_precision('Account'), string="Taxed", readonly=True)
    amount_tax = fields.Float(digits=dp.get_precision('Account'), string="Tax", readonly=True)
    amount_exempt = fields.Float(digits=dp.get_precision('Account'), string="Amount Exempt", readonly=True)
    #currency = fields.many2one('res.currency', string="Currency", readonly=True)
    cae = fields.Char('CAE', size=32, required=False, readonly=False)
    cae_due_date = fields.Date('CAE Due Date', readonly=False)
    date_process = fields.Datetime('Date Processed', readonly=True)
    infook = fields.Boolean('Info OK', default=False)
    # Expo fields
    customer_name = fields.Char(string='Customer Name', size=512)
    customer_address = fields.Char(string='Customer Address', size=512)
    board_perm_info = fields.Char(string='Boarding Permissions', size=512)
    dst_cuit_id = fields.Many2one('wsfex.dst_cuit.codes', 'Country CUIT')
    dst_country_id = fields.Many2one('wsfex.dst_country.codes', 'Dest Country')
    partner_id = fields.Many2one('res.partner', string='Partner')

    @api.onchange("invoice_id")
    def onchange_invoice(self):
        inv = self.invoice_id
        if inv:
            if inv.local:
                config_model = self.env["wsfe.config"]
            else:
                config_model = self.env["wsfex.config"]

            voucher_model = self.env['wsfe.voucher_type']
            voucher_type = voucher_model.get_voucher_type(inv, as_obj=True)
            pos_ar = inv.pos_ar_id
            self.pos_id = pos_ar.id
            self.voucher_type = voucher_type.id
            conf = config_model.get_config(pos_ar)
            self.config_id = "%s,%d" % (conf._name, conf.id)
        else:
            self.pos_id = False
            self.config_id = False
            self.voucher_type = False

    @api.onchange('config_id', 'voucher_type')
    def change_pos(self):
        #pos_model = self.env['pos.ar']
        ws_config = self.config_id
        if ws_config:
            ids = [p.id for p in ws_config.point_of_sale_ids]
            #denomination_id = self.voucher_type.denomination_id.id or False
            domain = [('id', 'in', ids)]
            #pos_ids = pos_model.search(domain)
            #if len(pos_ids) == 1:
            #    self.pos_id = pos_ids[0]
            return {'domain': {'pos_id': domain}}

        return {'domain': {}}

    @api.onchange('voucher_number')
    def change_voucher_number(self):

        voucher_type = self.voucher_type.code
        pos = int(self.pos_id.name)
        number = self.voucher_number

        if not voucher_type or not pos or not number:
            return

        res = self.config_id.get_voucher_info(pos, voucher_type, number)
        if self.invoice_id.local:
            doc_ids = self.env['res.document.type'].search([('afip_code', '=', res['DocTipo'])])
            document_type = doc_ids and doc_ids[0] or False
            di = time.strftime(DEFAULT_SERVER_DATE_FORMAT, time.strptime(str(res['CbteFch']),
                                                                         '%Y%m%d'))
            dd = time.strftime(DEFAULT_SERVER_DATE_FORMAT, time.strptime(str(res['FchVto']),
                                                                         '%Y%m%d'))
            dpr = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, time.strptime(
                str(res['FchProceso']), '%Y%m%d%H%M%S'))
    #
            # TODO: Tandriamos que filtrar las invoices por Tipo de Comprobante tambien
            # para ello podemos agregar un par de campos mas para usarlos como filtros,
            # por ejemplo, is_debit_note y type
            self.document_type = document_type
            self.document_number = str(res['DocNro'])
            self.date_invoice = di  # str(res['CbteFch']),
            self.amount_total = res['ImpTotal']
            self.amount_no_taxed = res['ImpTotConc']
            #'amount_untaxed':res['ImpNeto'],
            self.amount_taxed = res['ImpNeto']
            self.amount_tax = res['ImpIVA'] + res['ImpTrib']
            self.amount_exempt = res['ImpOpEx']
            #'currency':,
            self.cae = str(res['CodAutorizacion'])
            self.cae_due_date = dd
            self.date_process = dpr
            # Expo fields are set to False
            self.partner_id = False
            self.board_perm_info = False
            self.dst_country_id = False
            self.dst_cuit_id = False
            self.customer_name = False
            self.customer_address = False
        else:
            try:
                date_invoice = fields.Date.to_string(parse(res['Fecha_cbte']))
            except ValueError:
                date_invoice = False

            try:
                cae_due_date = fields.Date.to_string(parse(res['Fch_venc_Cae']))
            except ValueError:
                cae_due_date = False

            #try:
            #    date_process = fields.Date.to_string(parse(res['Fch_venc_Cae']))
            #except ValueError:
            #    pass

            customer_name = res.get("Cliente", "")
            document_number = res.get("ID_impositivo", "")
            partner = self.env['res.partner'].search(
                [
                    ("vat", "!=", False),
                    '|',
                    ("name", "ilike", customer_name),
                    ("vat", "=", document_number),
                ],
                limit=1,
                order="is_company desc",  # partners with is_company == True are fetched first
            )

            self.partner_id = partner.id
            self.document_type = partner.document_type_id.afip_code
            self.document_number = document_number
            self.customer_name = customer_name
            self.customer_address = res.get("Domicilio_cliente", "").strip()
            self.date_invoice = date_invoice
            self.amount_total = res['Imp_total']
            self.amount_no_taxed = res['Imp_total']
            self.amount_taxed = res['Imp_total']
            self.amount_tax = 0
            self.amount_exempt = 0
            self.cae = str(res['Cae'])
            self.cae_due_date = cae_due_date

            # Fetch destiny country id
            dst_cmp = res.get("Dst_cmp")
            if dst_cmp:
                self.dst_country_id = self.env["wsfex.dst_country.codes"].search(
                    [("code", "=", dst_cmp)]).id
            else:
                self.dst_country_id = False

            # Fetch destiny cuit id
            dst_cuit = res.get("Cuit_pais_cliente")
            if dst_cuit:
                self.dst_cuit_id = self.env["wsfex.dst_cuit.codes"].search(
                    [("code", "=", dst_cuit)]).id
            else:
                self.dst_cuit_id = False

            # Fetch Boarding Permission data
            PermisoExistente = res.get("Permiso_existente", "") or ""
            if PermisoExistente.upper() == "S":
                perms = res.get("Permisos")
                if perms:
                    self.board_perm_info = ", ".join(map(str, perms))

            date_process = False
            self.date_process = date_process

        self.infook = True

        domain = [
            ('amount_total', '=', self.amount_total),
            ('partner_id.vat', '=', self.document_number),
            ('amount_exempt', '=', self.amount_exempt),
            ('amount_taxed', '=', self.amount_taxed),
            ('amount_no_taxed', '=', self.amount_no_taxed),
            ('state', 'in', ('draft', 'proforma2', 'proforma'))]

        #invoice_ids = invoice_model.search(domain)
        #if len(invoice_ids) == 1:
        #    self.invoice_id = invoice_ids[0]

        return {'domain': {'invoice_id': domain}}

    @api.multi
    def relate_invoice(self):

        # Obtenemos los datos puestos por el usuario
        invoice = self.invoice_id

        if not self.infook:
            raise except_orm(_("WSFE Error"),
                    _("Sinchronize process is not correct!"))

        pos = int(self.pos_id.name)
        number = self.voucher_number
        date_invoice = self.date_invoice

        invoice.wsfe_relate_invoice(pos, number, date_invoice,
                                    self.cae, self.cae_due_date)

        return {'type': 'ir.actions.act_window_close'}
