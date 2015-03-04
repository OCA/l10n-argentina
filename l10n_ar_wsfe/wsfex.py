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
    _description = "WSFEX Currency Codes"

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
    _order = 'code'

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

#    def check_errors(self, cr, uid, res, raise_exception=True, context=None):
#        msg = ''
#        if 'errors' in res:
#            errors = [error.msg for error in res['errors']]
#            err_codes = [str(error.code) for error in res['errors']]
#            msg = ' '.join(errors)
#            msg = msg + ' Codigo/s Error:' + ' '.join(err_codes)
#
#            if msg != '' and raise_exception:
#                raise osv.except_osv(_('WSFE Error!'), msg)
#
#        return msg
#
#    def check_observations(self, cr, uid, res, context):
#        msg = ''
#        if 'observations' in res:
#            observations = [obs.msg for obs in res['observations']]
#            obs_codes = [str(obs.code) for obs in res['observations']]
#            msg = ' '.join(observations)
#            msg = msg + ' Codigo/s Observacion:' + ' '.join(obs_codes)
#
#            # Escribimos en el log del cliente web
#            self.log(cr, uid, None, msg, context)
#
#        return msg
#
#    def get_invoice_CAE(self, cr, uid, ids, invoice_ids, pos, voucher_type, details, context={}):
#        ta_obj = self.pool.get('wsaa.ta')
#
#        conf = self.browse(cr, uid, ids)[0]
#        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)
#
#        _wsfe = wsfe(conf.cuit, token, sign, conf.url)
#        res = _wsfe.fe_CAE_solicitar(pos, voucher_type, details)
#
#        return res
#
#    def _log_wsfe_request(self, cr, uid, ids, pos, voucher_type_code, details, res, context=None):
#        wsfe_req_obj = self.pool.get('wsfe.request')
#        voucher_type_obj = self.pool.get('wsfe.voucher_type')
#        voucher_type_ids = voucher_type_obj.search(cr, uid, [('code','=',voucher_type_code)])
#        voucher_type_name = voucher_type_obj.read(cr, uid, voucher_type_ids, ['name'])[0]['name']
#        req_details = []
#        for index, comp in enumerate(res['Comprobantes']):
#            detail = details[index]
#
#            # Esto es para fixear un bug que al hacer un refund, si fallaba algo con la AFIP
#            # se hace el rollback por lo tanto el refund que se estaba creando ya no existe en
#            # base de datos y estariamos violando una foreign key contraint. Por eso,
#            # chequeamos que existe info de la invoice_id, sino lo seteamos en False
#            read_inv = self.pool.get('account.invoice').read(cr, uid, detail['invoice_id'], ['id', 'internal_number'], context=context)
#
#            if not read_inv:
#                invoice_id = False
#            else:
#                invoice_id = detail['invoice_id']
#
#            det = {
#                'name': invoice_id,
#                'concept': str(detail['Concepto']),
#                'doctype': detail['DocTipo'], # TODO: Poner aca el nombre del tipo de documento
#                'docnum': str(detail['DocNro']),
#                'voucher_number': comp['CbteHasta'],
#                'voucher_date': comp['CbteFch'],
#                'amount_total': detail['ImpTotal'],
#                'cae': comp['CAE'],
#                'cae_duedate': comp['CAEFchVto'],
#                'result': comp['Resultado'],
#                'observations': '\n'.join(comp['Observaciones']),
#            }
#
#            req_details.append((0, 0, det))
#
#        # Chequeamos el reproceso
#        reprocess = False
#        if res['Reproceso'] == 'S':
#            reprocess = True
#
#        vals = {
#            'voucher_type': voucher_type_name,
#            'nregs': len(details),
#            'pos_ar': '%04d' % pos,
#            'date_request': time.strftime('%Y-%m-%d %H:%M:%S'),
#            'result': res['Resultado'],
#            'reprocess': reprocess,
#            'errors': '\n'.join(res['Errores']),
#            'detail_ids': req_details,
#            }
#
#        return wsfe_req_obj.create(cr, uid, vals)
#
#    def get_last_voucher(self, cr, uid, ids, pos, voucher_type, context={}):
#        ta_obj = self.pool.get('wsaa.ta')
#
#        conf = self.browse(cr, uid, ids)[0]
#        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)
#
#        _wsfe = wsfe(conf.cuit, token, sign, conf.url)
#        res = _wsfe.fe_comp_ultimo_autorizado(pos, voucher_type)
#
#        self.check_errors(cr, uid, res, context=context)
#        self.check_observations(cr, uid, res, context=context)
#        last = res['response'].CbteNro
#        return last
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
wsfex_config()
#
#class wsfe_voucher_type(osv.osv):
#    _name = "wsfe.voucher_type"
#    _description = "Voucher Type for Electronic Invoice"
#
#    _columns = {
#        'name': fields.char('Name', size=64, required=True, readonly=False, help='Voucher Type, eg.: Factura A, Nota de Credito B, etc.'),
#        'code': fields.char('Code', size=4, required=True, help='Internal Code assigned by AFIP for voucher type'),
#
#        'voucher_model': fields.selection([
#            ('invoice','Factura/NC/ND'),
#            ('voucher','Recibo'),],'Voucher Model', select=True, required=True),
#
#        'document_type' : fields.selection([
#            ('out_invoice','Factura'),
#            ('out_refund','Nota de Credito'),
#            ('out_debit','Nota de Debito'),
#            ],'Document Type', select=True, required=True, readonly=False),
#
#        'denomination_id': fields.many2one('invoice.denomination', 'Denomination', required=False),
#    }
#
#    """Es un comprobante que una empresa envía a su cliente, en la que se le notifica haber cargado o debitado en su cuenta una determinada suma o valor, por el concepto que se indica en la misma nota. Este documento incrementa el valor de la deuda o saldo de la cuenta, ya sea por un error en la facturación, interés por mora en el pago, o cualquier otra circunstancia que signifique el incremento del saldo de una cuenta.
#It is a proof that a company sends to your client, which is notified to be charged or debited the account a certain sum or value, the concept shown in the same note. This document increases the value of the debt or account balance, either by an error in billing, interest for late payment, or any other circumstance that means the increase in the balance of an account."""
#
#
#    def get_voucher_type(self, cr, uid, voucher, context=None):
#
#        # Chequeamos el modelo
#        voucher_model = None
#        model = voucher._table_name
#
#        if model == 'account.invoice':
#            voucher_model = 'invoice'
#
#            denomination_id = voucher.denomination_id.id
#            type = voucher.type
#            if type == 'out_invoice':
#                # TODO: Activar esto para ND
#                if voucher.is_debit_note:
#                    type = 'out_debit'
#
#            res = self.search(cr, uid, [('voucher_model','=',voucher_model), ('document_type','=',type), ('denomination_id','=',denomination_id)], context=context)
#
#            if not len(res):
#                raise osv.except_osv(_("Voucher type error!"), _("There is no voucher type that corresponds to this object"))
#
#            if len(res) > 1:
#                raise osv.except_osv(_("Voucher type error!"), _("There is more than one voucher type that corresponds to this object"))
#
#            return self.read(cr, uid, res[0], ['code'], context=context)['code']
#
#        elif model == 'account.voucher':
#            voucher_model = 'voucher'
#
#        return None
#
#wsfe_voucher_type()
