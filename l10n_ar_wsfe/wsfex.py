#' -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2015 E-MIPS (http://www.e-mips.com.ar) All Rights Reserved.
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
from wsfetools.wsfex_suds import WSFEX as wsfex
from datetime import datetime
import time

class wsfex_shipping_permission(osv.osv):
    _name = "wsfex.shipping.permission"
    _description = "WSFEX Shipping Permission"

    _columns = {
        'name' : fields.char('Code', required=True, size=16),
        'invoice_id' : fields.many2one('account.invoice', 'Invoice'),
        'dst_country_id' : fields.many2one('wsfex.dst_country.codes', 'Dest Country', required=True),
    }

wsfex_shipping_permission()

class wsfex_currency_codes(osv.osv):
    _name = "wsfex.currency.codes"
    _description = "WSFEX Currency Codes"
    _order = 'code'

    _columns = {
        'code' : fields.char('Code', required=True, size=4),
        'name' : fields.char('Desc', required=True, size=64),
        'currency_id' : fields.many2one('res.currency', string="OpenERP Currency"),
        'wsfex_config_id' : fields.many2one('wsfex.config'),
    }

wsfex_currency_codes()

class wsfex_uom_codes(osv.osv):
    _name = "wsfex.uom.codes"
    _description = "WSFEX UoM Codes"
    _order = 'code'

    _columns = {
        'code' : fields.integer('Code', required=True),
        'name' : fields.char('Desc', required=True, size=64),
        'uom_id' : fields.many2one('product.uom', string="OpenERP UoM"),
        'wsfex_config_id' : fields.many2one('wsfex.config'),
    }

wsfex_uom_codes()

class wsfex_lang_codes(osv.osv):
    _name = "wsfex.lang.codes"
    _description = "WSFEX Language Codes"
    _order = 'code'

    _columns = {
        'code' : fields.integer('Code', required=True),
        'name' : fields.char('Desc', required=True, size=64),
        'lang_id' : fields.many2one('res.lang', string="OpenERP Language"),
        'wsfex_config_id' : fields.many2one('wsfex.config'),
    }

wsfex_lang_codes()

class wsfex_dst_country_codes(osv.osv):
    _name = "wsfex.dst_country.codes"
    _description = "WSFEX Dest Country Codes"
    _order = 'name'

    _columns = {
        'code' : fields.char('Code', size=3, required=True),
        'name' : fields.char('Desc', required=True, size=64),
        'country_id' : fields.many2one('res.country', string="OpenERP Country"),
        'wsfex_config_id' : fields.many2one('wsfex.config'),
    }

wsfex_dst_country_codes()

class wsfex_incoterms_codes(osv.osv):
    _name = "wsfex.incoterms.codes"
    _description = "WSFEX Incoterms Codes"
    _order = 'code'

    _columns = {
        'code' : fields.char('Code', size=5, required=True),
        'name' : fields.char('Desc', required=True, size=64),
        'incoterms_id' : fields.many2one('stock.incoterms', string="OpenERP Incoterm"),
        'wsfex_config_id' : fields.many2one('wsfex.config'),
    }

wsfex_incoterms_codes()

class wsfex_dst_cuit_codes(osv.osv):
    _name = "wsfex.dst_cuit.codes"
    _description = "WSFEX DST CUIT Codes"
    _order = 'name'

    _columns = {
        'code' : fields.float('Code', digits=(12,0), required=True),
        'name' : fields.char('Desc', required=True, size=64),
        'wsfex_config_id' : fields.many2one('wsfex.config'),
    }

wsfex_dst_cuit_codes()

class wsfex_export_type_codes(osv.osv):
    _name = "wsfex.export_type.codes"
    _description = "WSFEX Export Type Codes"
    _order = 'code'

    _columns = {
        'code' : fields.integer('Code', required=True),
        'name' : fields.char('Desc', required=True, size=64),
        'wsfex_config_id' : fields.many2one('wsfex.config'),
    }

wsfex_export_type_codes()

class wsfex_voucher_type_codes(osv.osv):
    _name = "wsfex.voucher_type.codes"
    _description = "WSFEX Voucher Type Codes"
    _order = 'code'

    _columns = {
        'code' : fields.integer('Code', required=True),
        'name' : fields.char('Desc', required=True, size=64),
        'voucher_type_id' : fields.many2one('wsfe.voucher_type', string="OpenERP Voucher Type"),
        'wsfex_config_id' : fields.many2one('wsfex.config'),
    }

wsfex_voucher_type_codes()

class wsfex_config(osv.osv):
    _name = "wsfex.config"
    _description = "Configuration for WSFEX"

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'cuit': fields.related('company_id', 'partner_id', 'vat', type='char', string='Cuit'),
        'url' : fields.char('URL for WSFEX', size=60, required=True),
        'homologation' : fields.boolean('Homologation', help="If true, there will be some validations that are disabled, for example, invoice number correlativeness"),
        'point_of_sale_ids': fields.many2many('pos.ar', 'pos_ar_wsfex_rel', 'wsfex_config_id', 'pos_ar_id', 'Points of Sale'),
        'wsaa_ticket_id' : fields.many2one('wsaa.ta', 'Ticket Access'),
        'currency_ids' : fields.one2many('wsfex.currency.codes', 'wsfex_config_id' , 'Currencies'),
        'uom_ids' : fields.one2many('wsfex.uom.codes', 'wsfex_config_id' , 'Units of Measure'),
        'lang_ids' : fields.one2many('wsfex.lang.codes', 'wsfex_config_id' , 'Languages'),
        'country_ids' : fields.one2many('wsfex.dst_country.codes', 'wsfex_config_id' , 'Countries'),
        'incoterms_ids' : fields.one2many('wsfex.incoterms.codes', 'wsfex_config_id' , 'Incoterms'),
        'dst_cuit_ids' : fields.one2many('wsfex.dst_cuit.codes', 'wsfex_config_id' , 'DST CUIT'),
        'voucher_type_ids' : fields.one2many('wsfex.voucher_type.codes', 'wsfex_config_id' , 'Voucher Type'),
        'export_type_ids' : fields.one2many('wsfex.export_type.codes', 'wsfex_config_id' , 'Export Type'),
        'company_id' : fields.many2one('res.company', 'Company Name' , required=True),
    }

    _sql_constraints = [
        #('company_uniq', 'unique (company_id)', 'The configuration must be unique per company !')
    ]

    _defaults = {
        'company_id' : lambda self, cr, uid, context=None: self.pool.get('res.users')._get_company(cr, uid, context=context),
        'homologation': lambda *a: False,
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

    def get_config(self, cr, uid):
        # Obtenemos la compania que esta utilizando en este momento este usuario
        company_id = self.pool.get('res.users')._get_company(cr, uid)
        if not company_id:
            raise osv.except_osv(_('Company Error!'), _('There is no company being used by this user'))

        ids = self.search(cr, uid, [('company_id','=',company_id)])
        if not ids:
            raise osv.except_osv(_('WSFEX Config Error!'), _('There is no WSFEX configuration set to this company'))

        return self.browse(cr, uid, ids[0])

    def get_wsfex_currencies(self, cr, uid , ids , context={}):
        ta_obj = self.pool.get('wsaa.ta')

        conf = self.browse(cr, uid, ids)[0]
        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)

        _wsfex = wsfex(conf.cuit, token, sign, conf.url)
        res = _wsfex.FEXGetPARAM("MON") 

        wsfex_cur_obj = self.pool.get('wsfex.currency.codes')

#        # Chequeamos los errores
#        msg = self.check_errors(cr, uid, res, raise_exception=False, context=context)
#        if msg:
#            # TODO: Hacer un wrapping de los errores, porque algunos son
#            # largos y se imprimen muy mal en pantalla
#            raise osv.except_osv(_('Error reading taxes'), msg)

        # Armo un lista con los codigos de los Impuestos
        for r in res['response'][0]:
            res_c = wsfex_cur_obj.search(cr, uid , [('code','=', r.Mon_Id )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_cur_obj.create(cr, uid , {'code': r.Mon_Id, 'name': r.Mon_Ds, 'wsfex_config_id': ids[0]} , context={})
            #~ Si los codigos estan en la db los modifico
            else :
                wsfex_cur_obj.write(cr, uid , res_c[0] , {'name': r.Mon_Ds, 'wsfex_config_id': ids[0]})

        return True

    def get_wsfex_uoms(self, cr, uid , ids , context={}):
        ta_obj = self.pool.get('wsaa.ta')

        conf = self.browse(cr, uid, ids)[0]
        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)

        _wsfex = wsfex(conf.cuit, token, sign, conf.url)
        res = _wsfex.FEXGetPARAM("UMed") 

        wsfex_uom_obj = self.pool.get('wsfex.uom.codes')

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
            res_c = wsfex_uom_obj.search(cr, uid , [('code','=', r.Umed_Id )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_uom_obj.create(cr, uid , {'code': r.Umed_Id, 'name': r.Umed_Ds, 'wsfex_config_id': ids[0]} , context={})
            #~ Si los codigos estan en la db los modifico
            else :
                wsfex_uom_obj.write(cr, uid , res_c[0] , {'name': r.Umed_Ds, 'wsfex_config_id': ids[0]})

        return True

    def get_wsfex_langs(self, cr, uid , ids , context={}):
        ta_obj = self.pool.get('wsaa.ta')

        conf = self.browse(cr, uid, ids)[0]
        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)

        _wsfex = wsfex(conf.cuit, token, sign, conf.url)
        res = _wsfex.FEXGetPARAM("Idiomas") 

        wsfex_param_obj = self.pool.get('wsfex.lang.codes')

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
            res_c = wsfex_param_obj.search(cr, uid , [('code','=', r.Idi_Id )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create(cr, uid , {'code': r.Idi_Id, 'name': r.Idi_Ds, 'wsfex_config_id': ids[0]} , context={})
            #~ Si los codigos estan en la db los modifico
            else :
                wsfex_param_obj.write(cr, uid , res_c[0] , {'name': r.Idi_Ds, 'wsfex_config_id': ids[0]})

        return True

    def get_wsfex_export_types(self, cr, uid , ids , context={}):
        ta_obj = self.pool.get('wsaa.ta')

        conf = self.browse(cr, uid, ids)[0]
        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)

        _wsfex = wsfex(conf.cuit, token, sign, conf.url)
        res = _wsfex.FEXGetPARAM("Tipo_Expo") 

        wsfex_param_obj = self.pool.get('wsfex.export_type.codes')

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
            res_c = wsfex_param_obj.search(cr, uid , [('code','=', r.Tex_Id )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create(cr, uid , {'code': r.Tex_Id, 'name': r.Tex_Ds, 'wsfex_config_id': ids[0]} , context={})
            #~ Si los codigos estan en la db los modifico
            else :
                wsfex_param_obj.write(cr, uid , res_c[0] , {'name': r.Tex_Ds, 'wsfex_config_id': ids[0]})

        return True

    def get_wsfex_countries(self, cr, uid , ids , context={}):
        ta_obj = self.pool.get('wsaa.ta')

        conf = self.browse(cr, uid, ids)[0]
        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)

        _wsfex = wsfex(conf.cuit, token, sign, conf.url)
        res = _wsfex.FEXGetPARAM("DST_pais") 

        wsfex_param_obj = self.pool.get('wsfex.dst_country.codes')

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
            res_c = wsfex_param_obj.search(cr, uid , [('code','=', r.DST_Codigo )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create(cr, uid , {'code': r.DST_Codigo, 'name': r.DST_Ds, 'wsfex_config_id': ids[0]} , context={})
            #~ Si los codigos estan en la db los modifico
            else :
                wsfex_param_obj.write(cr, uid , res_c[0] , {'name': r.DST_Ds, 'wsfex_config_id': ids[0]})

        return True

    def get_wsfex_incoterms(self, cr, uid , ids , context={}):
        ta_obj = self.pool.get('wsaa.ta')

        conf = self.browse(cr, uid, ids)[0]
        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)

        _wsfex = wsfex(conf.cuit, token, sign, conf.url)
        res = _wsfex.FEXGetPARAM("Incoterms") 

        wsfex_param_obj = self.pool.get('wsfex.incoterms.codes')

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
            res_c = wsfex_param_obj.search(cr, uid , [('code','=', r.Inc_Id )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create(cr, uid , {'code': r.Inc_Id, 'name': r.Inc_Ds, 'wsfex_config_id': ids[0]} , context={})
            #~ Si los codigos estan en la db los modifico
            else :
                wsfex_param_obj.write(cr, uid , res_c[0] , {'name': r.Inc_Ds, 'wsfex_config_id': ids[0]})

        return True

    def get_wsfex_dst_cuits(self, cr, uid , ids , context={}):
        ta_obj = self.pool.get('wsaa.ta')

        conf = self.browse(cr, uid, ids)[0]
        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)

        _wsfex = wsfex(conf.cuit, token, sign, conf.url)
        res = _wsfex.FEXGetPARAM("DST_CUIT") 

        wsfex_param_obj = self.pool.get('wsfex.dst_cuit.codes')

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
            res_c = wsfex_param_obj.search(cr, uid , [('code','=', r.DST_CUIT )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create(cr, uid , {'code': r.DST_CUIT, 'name': r.DST_Ds, 'wsfex_config_id': ids[0]} , context={})
            #~ Si los codigos estan en la db los modifico
            else :
                wsfex_param_obj.write(cr, uid , res_c[0] , {'name': r.DST_Ds, 'wsfex_config_id': ids[0]})

        return True

    def get_wsfex_voucher_types(self, cr, uid , ids , context={}):
        ta_obj = self.pool.get('wsaa.ta')

        conf = self.browse(cr, uid, ids)[0]
        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)

        _wsfex = wsfex(conf.cuit, token, sign, conf.url)
        res = _wsfex.FEXGetPARAM("Tipo_Cbte") 

        wsfex_param_obj = self.pool.get('wsfex.voucher_type.codes')

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
            res_c = wsfex_param_obj.search(cr, uid , [('code','=', r.Cbte_Id )])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create(cr, uid , {'code': r.Cbte_Id, 'name': r.Cbte_Ds, 'wsfex_config_id': ids[0]} , context={})
            #~ Si los codigos estan en la db los modifico
            else :
                wsfex_param_obj.write(cr, uid , res_c[0] , {'name': r.Cbte_Ds, 'wsfex_config_id': ids[0]})

        return True

    def check_error(self, cr, uid, res, raise_exception=True, context=None):
        msg = ''
        if 'error' in res:
            error = res['error'].msg
            err_code = str(res['error'].code)
            msg = 'Codigo/s Error: %s[%s]' % (error, err_code)

            if msg != '' and raise_exception:
                raise osv.except_osv(_('WSFE Error!'), msg)

        return msg

    def check_event(self, cr, uid, res, context):
        msg = ''
        if 'event' in res:
            event = res['event'].msg
            eve_code = str(res['event'].code)
            msg = 'Codigo/s Observacion: %s [%s]' % (event, eve_code)

            # Escribimos en el log del cliente web
            #self.log(cr, uid, None, msg, context)

        return msg

    def get_invoice_CAE(self, cr, uid, ids, invoice_ids, pos, voucher_type, details, context={}):
        ta_obj = self.pool.get('wsaa.ta')

        conf = self.browse(cr, uid, ids)[0]
        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)

        _wsfex = wsfex(conf.cuit, token, sign, conf.url)

        # Agregamos la info que falta
        details['Tipo_cbte'] = voucher_type
        details['Punto_vta'] = pos
        res = _wsfex.FEXAuthorize(details)

        return res

    def _parse_result(self, cr, uid, ids, invoice_ids, result, context=None):

        invoice_obj = self.pool.get('account.invoice')

        if not context:
            context = {}

        invoices_approbed = {}

        # Verificamos el resultado de la Operacion
        # Si no fue aprobado
        if 'error' in result:

            msg = result['error'].msg
            if context.get('raise-exception', True):
                raise osv.except_osv(_('AFIP Web Service Error'),
                                     _('La factura no fue aprobada. \n%s') % msg)

        # Igualmente, siempre va a ser una para FExp
        for inv in invoice_obj.browse(cr, uid, invoice_ids):
            invoice_vals = {}

            comp = result['response']

            # Chequeamos que se corresponda con la factura que enviamos a validar
            doc_num = comp['Cuit'] == int(inv.partner_id.vat)
            cbte = True
            if inv.internal_number:
                cbte = comp['Cbte_nro'] == int(inv.internal_number.split('-')[1])
            else:
                # TODO: El nro de factura deberia unificarse para que se setee en una funcion
                # o algo asi para que no haya posibilidad de que sea diferente nunca en su formato
                invoice_vals['internal_number'] = '%04d-%08d' % (result['PtoVta'], comp['CbteHasta'])

            if not all([doc_num, cbte]):
                raise osv.except_osv(_("WSFE Error!"), _("Validated invoice that not corresponds!"))

            invoice_vals['cae'] = comp['Cae']
            invoice_vals['cae_due_date'] = comp['Fch_venc_Cae']
            invoices_approbed[inv.id] = invoice_vals

        return invoices_approbed

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

    def get_last_voucher(self, cr, uid, ids, pos, voucher_type, context={}):
        ta_obj = self.pool.get('wsaa.ta')

        conf = self.browse(cr, uid, ids)[0]
        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)

        _wsfe = wsfex(conf.cuit, token, sign, conf.url)
        res = _wsfe.FEXGetLast_CMP(pos, voucher_type)

        self.check_error(cr, uid, res, context=context)
        self.check_event(cr, uid, res, context=context)
        last = res['response']
        return last
#
#    def get_voucher_info(self, cr, uid, ids, pos, voucher_type, number, context={}):
#        ta_obj = self.pool.get('wsaa.ta')
#
#        conf = self.browse(cr, uid, ids)[0]
#        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)
#
#        _wsfe = wsfe(conf.cuit, token, sign, conf.url)
#        res = _wsfe.fe_comp_consultar(pos, voucher_type, number)
#
#        self.check_errors(cr, uid, res, context=context)
#        self.check_observations(cr, uid, res, context=context)
#        #last = res['response'].CbteNro
#
#        res = res['response']
#
#        result = {
#            'DocTipo' : res[0].DocTipo,
#            'DocNro' : res[0].DocNro,
#            'CbteDesde' : res[0].CbteDesde,
#            'CbteHasta' : res[0].CbteHasta,
#            'CbteFch' : res[0].CbteFch,
#            'ImpTotal' : res[0].ImpTotal,
#            'ImpTotConc' : res[0].ImpTotConc,
#            'ImpNeto' : res[0].ImpNeto,
#            'ImpOpEx' : res[0].ImpOpEx,
#            'ImpTrib' : res[0].ImpTrib,
#            'ImpIVA' : res[0].ImpIVA,
#            'FchServDesde' : res[0].FchServDesde,
#            'FchServHasta' : res[0].FchServHasta,
#            'FchVtoPago' : res[0].FchVtoPago,
#            'MonId' : res[0].MonId,
#            'MonCotiz' : res[0].MonCotiz,
#            'Resultado' : res[0].Resultado,
#            'CodAutorizacion' : res[0].CodAutorizacion,
#            'EmisionTipo' : res[0].EmisionTipo,
#            'FchVto' : res[0].FchVto,
#            'FchProceso' : res[0].FchProceso,
#            'PtoVta' : res[0].PtoVta,
#            'CbteTipo' : res[0].CbteTipo,
#        }
#
#        return result
#
#    def read_tax(self, cr, uid , ids , context={}):
#        ta_obj = self.pool.get('wsaa.ta')
#
#        conf = self.browse(cr, uid, ids)[0]
#        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)
#
#        _wsfe = wsfe(conf.cuit, token, sign, conf.url)
#        res = _wsfe.fe_param_get_tipos_iva()
#
#        wsfe_tax_obj = self.pool.get('wsfe.tax.codes')
#
#        # Chequeamos los errores
#        msg = self.check_errors(cr, uid, res, raise_exception=False, context=context)
#        if msg:
#            # TODO: Hacer un wrapping de los errores, porque algunos son
#            # largos y se imprimen muy mal en pantalla
#            raise osv.except_osv(_('Error reading taxes'), msg)
#
#        #~ Armo un lista con los codigos de los Impuestos
#        for r in res['response']:
#            res_c = wsfe_tax_obj.search(cr, uid , [('code','=', r.Id )])
#
#            #~ Si tengo no los codigos de esos Impuestos en la db, los creo
#            if not len(res_c):
#                fd = datetime.strptime(r.FchDesde, '%Y%m%d')
#                try:
#                    td = datetime.strptime(r.FchHasta, '%Y%m%d')
#                except ValueError:
#                    td = False
#
#                wsfe_tax_obj.create(cr, uid , {'code': r.Id, 'name': r.Desc, 'to_date': td,
#                        'from_date': fd, 'wsfe_config_id': ids[0], 'from_afip': True } , context={})
#            #~ Si los codigos estan en la db los modifico
#            else :
#                fd = datetime.strptime(r.FchDesde, '%Y%m%d')
#                #'NULL' ?? viene asi de fe_param_get_tipos_iva():
#                try:
#                    td = datetime.strptime(r.FchHasta, '%Y%m%d')
#                except ValueError:
#                    td = False
#
#                wsfe_tax_obj.write(cr, uid , res_c[0] , {'code': r.Id, 'name': r.Desc, 'to_date': td ,
#                    'from_date': fd, 'wsfe_config_id': ids[0], 'from_afip': True } )
#
#        return True
#

    def prepare_details(self, cr, uid, conf, invoice_ids, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid)
        #obj_precision = self.pool.get('decimal.precision')
        voucher_type_obj = self.pool.get('wsfe.voucher_type')
        invoice_obj = self.pool.get('account.invoice')
        currency_code_obj = self.pool.get('wsfex.currency.codes')
        uom_code_obj = self.pool.get('wsfex.uom.codes')

        if len(invoice_ids) > 1:
            raise osv.except_osv(_("WSFEX Error!"), _("You cannot inform more than one invoice to AFIP WSFEX"))

        first_num = context.get('first_num', False)
        Id = int(datetime.strftime(datetime.now(), '%Y%m%d%H%M%S'))
        cbte_nro = 0

        inv = invoice_obj.browse(cr, uid, invoice_ids[0], context=context)

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
        curr_code_ids = currency_code_obj.search(cr, uid, [('currency_id', '=', inv_currency_id)], context=context)

        if curr_code_ids:
            curr_code = currency_code_obj.read(cr, uid, curr_code_ids[0], {'code'}, context=context)['code']
        else:
            raise osv.except_osv(_("WSFEX Error!"), _("Currency %s has not code configured") % inv.currency_id.name)

        # Items
        items = []
        for i, line in enumerate(inv.invoice_line):
            product_id = line.product_id
            product_code = product_id and product_id.default_code or i
            uom_id = line.uos_id.id
            uom_code_ids = uom_code_obj.search(cr, uid, [('uom_id','=',uom_id)], context=context)
            if not uom_code_ids:
                raise osv.except_osv(_("WSFEX Error!"), _("There is no UoM Code defined for %s in line %s") % (line.uos_id.name, line.name))

            uom_code = uom_code_obj.read(cr, uid, uom_code_ids[0], {'code'}, context=context)['code']

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
            tipo_cbte = voucher_type_obj.get_voucher_type(cr, uid, associated_inv, context=context)
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
