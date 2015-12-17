# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2015 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2015 Eynes (http://www.eynes.com.ar)
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

from openerp.osv import osv
from openerp import models, fields, api
from openerp.tools.translate import _
from wsfetools.wsfex_suds import WSFEX as wsfex
from datetime import datetime
import time


class wsfex_shipping_permission(models.Model):
    _name = "wsfex.shipping.permission"
    _description = "WSFEX Shipping Permission"

    name = fields.Char('Code', required=True, size=16)
    invoice_id = fields.Many2one('account.invoice', 'Invoice')
    dst_country_id = fields.Many2one('wsfex.dst_country.codes', 'Dest Country', required=True)

wsfex_shipping_permission()

class wsfex_currency_codes(models.Model):
    _name = "wsfex.currency.codes"
    _description = "WSFEX Currency Codes"
    _order = 'code'

    code = fields.Char('Code', required=True, size=4)
    name = fields.Char('Desc', required=True, size=64)
    currency_id = fields.Many2one('res.currency', string="OpenERP Currency")
    wsfex_config_id = fields.Many2one('wsfex.config')

wsfex_currency_codes()

class wsfex_uom_codes(models.Model):
    _name = "wsfex.uom.codes"
    _description = "WSFEX UoM Codes"
    _order = 'code'

    code = fields.Integer('Code', required=True)
    name = fields.Char('Desc', required=True, size=64)
    uom_id = fields.Many2one('product.uom', string="OpenERP UoM")
    wsfex_config_id = fields.Many2one('wsfex.config')

wsfex_uom_codes()

class wsfex_lang_codes(models.Model):
    _name = "wsfex.lang.codes"
    _description = "WSFEX Language Codes"
    _order = 'code'

    code = fields.Integer('Code', required=True)
    name = fields.Char('Desc', required=True, size=64)
    lang_id = fields.Many2one('res.lang', string="OpenERP Language")
    wsfex_config_id = fields.Many2one('wsfex.config')

wsfex_lang_codes()

class wsfex_dst_country_codes(models.Model):
    _name = "wsfex.dst_country.codes"
    _description = "WSFEX Dest Country Codes"
    _order = 'name'

    code = fields.Char('Code', size=3, required=True)
    name = fields.Char('Desc', required=True, size=64)
    country_id = fields.Many2one('res.country', string="OpenERP Country")
    wsfex_config_id = fields.Many2one('wsfex.config')

wsfex_dst_country_codes()

class wsfex_incoterms_codes(models.Model):
    _name = "wsfex.incoterms.codes"
    _description = "WSFEX Incoterms Codes"
    _order = 'code'

    code = fields.Char('Code', size=5, required=True)
    name = fields.Char('Desc', required=True, size=64)
    incoterms_id = fields.Many2one('stock.incoterms', string="OpenERP Incoterm")
    wsfex_config_id = fields.Many2one('wsfex.config')

wsfex_incoterms_codes()

class wsfex_dst_cuit_codes(models.Model):
    _name = "wsfex.dst_cuit.codes"
    _description = "WSFEX DST CUIT Codes"
    _order = 'name'

    code = fields.Float('Code', digits=(12,0), required=True)
    name = fields.Char('Desc', required=True, size=64)
    wsfex_config_id = fields.Many2one('wsfex.config')

wsfex_dst_cuit_codes()

class wsfex_export_type_codes(models.Model):
    _name = "wsfex.export_type.codes"
    _description = "WSFEX Export Type Codes"
    _order = 'code'

    code = fields.Integer('Code', required=True)
    name = fields.Char('Desc', required=True, size=64)
    wsfex_config_id = fields.Many2one('wsfex.config')

wsfex_export_type_codes()

class wsfex_voucher_type_codes(models.Model):
    _name = "wsfex.voucher_type.codes"
    _description = "WSFEX Voucher Type Codes"
    _order = 'code'

    code = fields.Integer('Code', required=True)
    name = fields.Char('Desc', required=True, size=64)
    voucher_type_id = fields.Many2one('wsfe.voucher_type', string="OpenERP Voucher Type")
    wsfex_config_id = fields.Many2one('wsfex.config')

wsfex_voucher_type_codes()

class wsfex_config(models.Model):
    _name = "wsfex.config"
    _description = "Configuration for WSFEX"

    name = fields.Char('Name', size=64, required=True)
    cuit = fields.Char(related='company_id.partner_id.vat', string='Cuit')
    url = fields.Char('URL for WSFEX', size=60, required=True)
    homologation = fields.Boolean('Homologation', default=False,
            help="If true, there will be some validations that are disabled, for example, invoice number correlativeness")
    point_of_sale_ids = fields.Many2many('pos.ar', 'pos_ar_wsfex_rel', 'wsfex_config_id', 'pos_ar_id', 'Points of Sale')
    wsaa_ticket_id = fields.Many2one('wsaa.ta', 'Ticket Access')
    currency_ids = fields.One2many('wsfex.currency.codes', 'wsfex_config_id' , 'Currencies')
    uom_ids = fields.One2many('wsfex.uom.codes', 'wsfex_config_id' , 'Units of Measure')
    lang_ids = fields.One2many('wsfex.lang.codes', 'wsfex_config_id' , 'Languages')
    country_ids = fields.One2many('wsfex.dst_country.codes', 'wsfex_config_id' , 'Countries')
    incoterms_ids = fields.One2many('wsfex.incoterms.codes', 'wsfex_config_id' , 'Incoterms')
    dst_cuit_ids = fields.One2many('wsfex.dst_cuit.codes', 'wsfex_config_id' , 'DST CUIT')
    voucher_type_ids = fields.One2many('wsfex.voucher_type.codes', 'wsfex_config_id' , 'Voucher Type')
    export_type_ids = fields.One2many('wsfex.export_type.codes', 'wsfex_config_id' , 'Export Type')
    company_id = fields.Many2one('res.company', 'Company Name' , required=True)

    _sql_constraints = [
        #('company_uniq', 'unique (company_id)', 'The configuration must be unique per company !')
    ]

    _defaults = {
        'company_id' : lambda self, cr, uid, context=None: self.pool.get('res.users')._get_company(cr, uid, context=context),
        }

    def create(self, cr, uid, vals, context):
        # Creamos tambien un TA para este servcio y esta compania
        ta_obj = self.pool.get('wsaa.ta')
        wsaa_obj = self.pool.get('wsaa.config')
        service_obj = self.pool.get('afipws.service')

        # Buscamos primero el wsaa que corresponde a esta compania
        # porque hay que recordar que son unicos por compania
        wsaa_ids = wsaa_obj.search(cr, uid, [('company_id','=', vals['company_id'])], context=context)
        service_ids = service_obj.search(cr, uid, [('name','=', 'wsfex')], context=context)
        if wsaa_ids:
            ta_vals = {
                'name': service_ids[0],
                'company_id': vals['company_id'],
                'config_id' : wsaa_ids[0],
                }

            ta_id = ta_obj.create(cr, uid, ta_vals, context)
            vals['wsaa_ticket_id'] = ta_id

        return super(wsfex_config, self).create(cr, uid, vals, context)

    def get_config(self):
        # Obtenemos la compania que esta utilizando en este momento este usuario
        company_id = self.env.user.company_id.id
        if not company_id:
            raise osv.except_osv(_('Company Error!'), _('There is no company being used by this user'))

        ids = self.search([('company_id','=',company_id)])
        if not ids:
            raise osv.except_osv(_('WSFEX Config Error!'), _('There is no WSFEX configuration set to this company'))

        return ids

    @api.one
    def get_wsfex_currencies(self):
        conf = self

        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfex = wsfex(self.cuit, token, sign, self.url)
        res = _wsfex.FEXGetPARAM("MON")

        wsfex_cur_obj = self.env['wsfex.currency.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res['response'][0]:
            res_c = wsfex_cur_obj.search([('code','=', r.Mon_Id )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_cur_obj.create({'code': r.Mon_Id, 'name': r.Mon_Ds, 'wsfex_config_id': self.id})
            #~ Si los codigos estan en la db los modifico
            else :
                res_c.write({'name': r.Mon_Ds, 'wsfex_config_id': self.id})

        return True

    @api.one
    def get_wsfex_uoms(self):
        conf = self

        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfex = wsfex(self.cuit, token, sign, self.url)
        res = _wsfex.FEXGetPARAM("UMed")

        wsfex_uom_obj = self.env['wsfex.uom.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res['response'][0]:
            # El servicio de AFIP me devuelve dentro de la lista
            # unos valores None
            if not r:
                continue
            res_c = wsfex_uom_obj.search([('code','=', r.Umed_Id )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_uom_obj.create({'code': r.Umed_Id, 'name': r.Umed_Ds, 'wsfex_config_id': self.id})
            #~ Si los codigos estan en la db los modifico
            else :
                res_c.write({'name': r.Umed_Ds, 'wsfex_config_id': self.id})

        return True

    @api.one
    def get_wsfex_langs(self):
        conf = self

        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfex = wsfex(self.cuit, token, sign, self.url)
        res = _wsfex.FEXGetPARAM("Idiomas")

        wsfex_param_obj = self.env['wsfex.lang.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res['response'][0]:
            # El servicio de AFIP me devuelve dentro de la lista
            # unos valores None
            if not r:
                continue
            res_c = wsfex_param_obj.search([('code','=', r.Idi_Id )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create({'code': r.Idi_Id, 'name': r.Idi_Ds, 'wsfex_config_id': self.id})
            #~ Si los codigos estan en la db los modifico
            else :
                res_c.write({'name': r.Idi_Ds, 'wsfex_config_id': self.id})

        return True


    @api.one
    def get_wsfex_export_types(self):
        conf = self

        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfex = wsfex(self.cuit, token, sign, self.url)
        res = _wsfex.FEXGetPARAM("Tipo_Expo")

        wsfex_param_obj = self.env['wsfex.export_type.codes']

#        # Chequeamos los errores
#        msg = self.check_errors(cr, uid, res, raise_exception=False, context=context)
#        if msg:
#            # TODO: Hacer un wrapping de los errores, porque algunos son
#            # largos y se imprimen muy mal en pantalla
#            raise osv.except_osv(_('Error reading taxes'), msg)

        # Armo un lista con los codigos de los Impuestos
        for r in res['response'][0]:
            # El servicio de AFIP me devuelve dentro de la lista
            # unos valores None
            if not r:
                continue
            res_c = wsfex_param_obj.search([('code','=', r.Tex_Id )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create({'code': r.Tex_Id, 'name': r.Tex_Ds, 'wsfex_config_id': self.id})
            #~ Si los codigos estan en la db los modifico
            else :
                res_c.write({'name': r.Tex_Ds, 'wsfex_config_id': self.id})

        return True


    @api.one
    def get_wsfex_countries(self):
        conf = self

        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfex = wsfex(self.cuit, token, sign, self.url)
        res = _wsfex.FEXGetPARAM("DST_pais")

        wsfex_param_obj = self.env['wsfex.dst_country.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res['response'][0]:
            # El servicio de AFIP me devuelve dentro de la lista
            # unos valores None
            if not r:
                continue
            res_c = wsfex_param_obj.search([('code','=', r.DST_Codigo )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create({'code': r.DST_Codigo, 'name': r.DST_Ds, 'wsfex_config_id': self.id})
            #~ Si los codigos estan en la db los modifico
            else :
                res_c.write({'name': r.DST_Ds, 'wsfex_config_id': self.id})

        return True

    @api.one
    def get_wsfex_incoterms(self):
        conf = self

        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfex = wsfex(self.cuit, token, sign, self.url)
        res = _wsfex.FEXGetPARAM("Incoterms")

        wsfex_param_obj = self.env['wsfex.incoterms.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res['response'][0]:
            # El servicio de AFIP me devuelve dentro de la lista
            # unos valores None
            if not r:
                continue
            res_c = wsfex_param_obj.search([('code','=', r.Inc_Id )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create({'code': r.Inc_Id, 'name': r.Inc_Ds, 'wsfex_config_id': self.id})
            #~ Si los codigos estan en la db los modifico
            else :
                res_c.write({'name': r.Inc_Ds, 'wsfex_config_id': self.id})

        return True

    @api.one
    def get_wsfex_dst_cuits(self):
        conf = self

        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfex = wsfex(self.cuit, token, sign, self.url)
        res = _wsfex.FEXGetPARAM("DST_CUIT")

        wsfex_param_obj = self.env['wsfex.dst_cuit.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res['response'][0]:
            # El servicio de AFIP me devuelve dentro de la lista
            # unos valores None
            if not r:
                continue
            res_c = wsfex_param_obj.search([('code','=', r.DST_CUIT )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create({'code': r.DST_CUIT, 'name': r.DST_Ds, 'wsfex_config_id': self.id})
            #~ Si los codigos estan en la db los modifico
            else :
                res_c.write({'name': r.DST_Ds, 'wsfex_config_id': self.id})

        return True

    @api.one
    def get_wsfex_voucher_types(self):
        conf = self

        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfex = wsfex(self.cuit, token, sign, self.url)
        res = _wsfex.FEXGetPARAM("Tipo_Cbte")

        wsfex_param_obj = self.env['wsfex.voucher_type.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res['response'][0]:
            # El servicio de AFIP me devuelve dentro de la lista
            # unos valores None
            if not r:
                continue
            res_c = wsfex_param_obj.search([('code','=', r.Cbte_Id )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create({'code': r.Cbte_Id, 'name': r.Cbte_Ds, 'wsfex_config_id': self.id})
            #~ Si los codigos estan en la db los modifico
            else :
                res_c.write({'name': r.Cbte_Ds, 'wsfex_config_id': self.id})

        return True

    def check_error(self, res, raise_exception=True):
        msg = ''
        if 'error' in res:
            error = res['error'].msg
            err_code = str(res['error'].code)
            msg = 'Codigo/s Error: %s[%s]' % (error, err_code)

            if msg != '' and raise_exception:
                raise osv.except_osv(_('WSFE Error!'), msg)

        return msg

    def check_event(self, res):
        msg = ''
        if 'event' in res:
            event = res['event'].msg
            eve_code = str(res['event'].code)
            msg = 'Codigo/s Observacion: %s [%s]' % (event, eve_code)

            # TODO: Donde lo ponemos a esto?
            # Escribimos en el log del cliente web
            #self.log(cr, uid, None, msg, context)

        return msg

    @api.multi
    def get_invoice_CAE(self, pos, voucher_type, details):
        conf = self
        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfex = wsfex(conf.cuit, token, sign, conf.url)

        # Agregamos la info que falta
        details['Tipo_cbte'] = voucher_type
        details['Punto_vta'] = pos
        res = _wsfex.FEXAuthorize(details)

        return res

    def _parse_result(self, invoices, result):

        invoices_approbed = {}

        # Verificamos el resultado de la Operacion
        # Si no fue aprobado
        if 'error' in result:

            msg = result['error'].msg
            if self._context.get('raise-exception', True):
                raise osv.except_osv(_('AFIP Web Service Error'),
                                     _('La factura no fue aprobada. \n%s') % msg)

        # Igualmente, siempre va a ser una para FExp
        for inv in invoices:
            invoice_vals = {}

            comp = result['response']

            # Chequeamos que se corresponda con la factura que enviamos a validar
            #doc_num = comp['Cuit'] == int(inv.partner_id.vat)
            cbte = True
            if inv.internal_number:
                cbte = comp['Cbte_nro'] == int(inv.internal_number.split('-')[1])
            else:
                # TODO: El nro de factura deberia unificarse para que se setee en una funcion
                # o algo asi para que no haya posibilidad de que sea diferente nunca en su formato
                invoice_vals['internal_number'] = '%04d-%08d' % (result['PtoVta'], comp['CbteHasta'])

            if not all([cbte]):
                raise osv.except_osv(_("WSFE Error!"), _("Validated invoice that not corresponds!"))

            invoice_vals['cae'] = comp['Cae']
            invoice_vals['cae_due_date'] = comp['Fch_venc_Cae']
            invoices_approbed[inv.id] = invoice_vals

        return invoices_approbed

    # TODO: Migrar a v8
    def _log_wsfe_request(self, cr, uid, ids, pos, voucher_type_code, detail, res, context=None):

        wsfex_req_obj = self.pool.get('wsfex.request.detail')
        voucher_type_obj = self.pool.get('wsfe.voucher_type')
        voucher_type_ids = voucher_type_obj.search(cr, uid, [('code','=',voucher_type_code)])
        #voucher_type_name = voucher_type_obj.read(cr, uid, voucher_type_ids, ['name'])[0]['name']

        error = 'error' in res

        # Esto es para fixear un bug que al hacer un refund, si fallaba algo con la AFIP
        # se hace el rollback por lo tanto el refund que se estaba creando ya no existe en
        # base de datos y estariamos violando una foreign key contraint. Por eso,
        # chequeamos que existe info de la invoice_id, sino lo seteamos en False
        read_inv = self.pool.get('account.invoice').read(cr, uid, detail['invoice_id'], ['id', 'internal_number'], context=context)

        if not read_inv:
            invoice_id = False
        else:
            invoice_id = detail['invoice_id']

        vals = {
            'invoice_id': invoice_id,
            'request_id': detail['Id'],
            'voucher_number': '%04d-%08d' % (pos, detail['Cbte_nro']),
            'voucher_type_id': voucher_type_ids[0],
            'date': detail['Fecha_cbte'],
            'detail': str(detail),
            'error': 'error' in res and res['error'] or '',
            'event': 'event' in res and res['event'] or '',
        }

        if not error:
            comp = res['response']
            vals['cae'] = comp['Cae']
            vals['cae_duedate'] = comp['Fch_venc_Cae']
            vals['result'] = comp['Resultado']
            vals['reprocess'] = comp['Reproceso']
        else:
            vals['result'] = 'R'

        return wsfex_req_obj.create(cr, uid, vals)

    # TODO: Migrar a v8
    def get_last_voucher(self, pos, voucher_type):
        conf = self

        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfe = wsfex(conf.cuit, token, sign, conf.url)
        res = _wsfe.FEXGetLast_CMP(pos, voucher_type)

        self.check_error(res)
        self.check_event(res)
        last = res['response']
        return last

    def prepare_details(self, invoices):
        company = self.env.user.company_id
        obj_precision = self.env['decimal.precision']
        voucher_type_obj = self.env['wsfe.voucher_type']
        invoice_obj = self.env['account.invoice']
        currency_code_obj = self.env['wsfex.currency.codes']
        uom_code_obj = self.env['wsfex.uom.codes']

        if len(invoices) > 1:
            raise osv.except_osv(_("WSFEX Error!"), _("You cannot inform more than one invoice to AFIP WSFEX"))

        first_num = self._context.get('first_num', False)
        Id = int(datetime.strftime(datetime.now(), '%Y%m%d%H%M%S'))
        cbte_nro = 0

        for inv in invoices:

            # Obtenemos el numero de comprobante a enviar a la AFIP teniendo en
            # cuenta que inv.number == 000X-00000NN o algo similar.
            if not inv.internal_number:
                if not first_num:
                    raise osv.except_osv(_("WSFE Error!"), _("There is no first invoice number declared!"))
                inv_number = first_num
            else:
                inv_number = inv.internal_number

            if not cbte_nro:
                cbte_nro = inv_number.split('-')[1]
                cbte_nro = int(cbte_nro)
            else:
                cbte_nro = cbte_nro + 1

            date_invoice = datetime.strptime(inv.date_invoice, '%Y-%m-%d')
            formatted_date_invoice = date_invoice.strftime('%Y%m%d')
            #date_due = inv.date_due and datetime.strptime(inv.date_due, '%Y-%m-%d').strftime('%Y%m%d') or formatted_date_invoice

            cuit_pais = inv.dst_cuit_id and inv.dst_cuit_id.code or 0
            inv_currency_id = inv.currency_id.id
            curr_codes = currency_code_obj.search([('currency_id', '=', inv_currency_id)])

            if curr_codes:
                curr_code = curr_codes[0].code
            else:
                raise osv.except_osv(_("WSFEX Error!"), _("Currency %s has not code configured") % inv.currency_id.name)

            # Items
            items = []
            for i, line in enumerate(inv.invoice_line):
                product_id = line.product_id
                product_code = product_id and product_id.default_code or i
                uom_id = line.uos_id.id
                uom_codes = uom_code_obj.search([('uom_id','=',uom_id)])
                if not uom_codes:
                    raise osv.except_osv(_("WSFEX Error!"), _("There is no UoM Code defined for %s in line %s") % (line.uos_id.name, line.name))

                uom_code = uom_codes[0].code

                items.append({
                    'Pro_codigo' : i,#product_code,
                    'Pro_ds' : line.name,
                    'Pro_qty' : line.quantity,
                    'Pro_umed' : uom_code,
                    'Pro_precio_uni' : line.price_unit,
                    'Pro_total_item' : line.price_subtotal,
                    'Pro_bonificacion' : 0,
                })

            Cmps_asoc = []
            for associated_inv in inv.associated_inv_ids:
                tipo_cbte = voucher_type_obj.get_voucher_type(associated_inv)
                pos, number = associated_inv.internal_number.split('-')
                Cmp_asoc = {
                    'Cbte_tipo': tipo_cbte,
                    'Cbte_punto_vta': int(pos),
                    'Cbte_nro': int(number),
                }

                Cmps_asoc.append(Cmp_asoc)

            Cmp = {
                'invoice_id' : inv.id,
                'Id' : Id,
                #'Tipo_cbte' : cbte_tipo,
                'Fecha_cbte' : formatted_date_invoice,
                #'Punto_vta' : pto_venta,
                'Cbte_nro' : cbte_nro,
                'Tipo_expo' : inv.export_type_id.code, #Exportacion de bienes
                'Permiso_existente' : '', # TODO: manejo de permisos de embarque
                'Dst_cmp' : inv.dst_country_id.code,
                'Cliente' : inv.partner_id.name,
                'Domicilio_cliente' : inv.partner_id.contact_address,
                'Cuit_pais_cliente' : cuit_pais,
                'Id_impositivo' : inv.partner_id.vat,
                'Moneda_Id' : curr_code,
                'Moneda_ctz' : 1.000000, # TODO: Obtener cotizacion usando el metodo de AFIP
                'Imp_total' : inv.amount_total,
                'Idioma_cbte' : 1,
                'Items' : items
            }

            # Datos No Obligatorios
            if inv.incoterm_id:
                Cmp['Incoterms'] = inv.incoterm_id.code
                Cmp['Incoterms_Ds'] = inv.incoterm_id.name

            if Cmps_asoc:
                Cmp['Cmps_Asoc'] = Cmps_asoc
        return Cmp

wsfex_config()
