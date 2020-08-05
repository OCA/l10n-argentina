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

from datetime import datetime
from operator import attrgetter

from openerp import _, api, exceptions, fields, models
from openerp.osv import osv

from ..wsfetools.wsfex_suds import WSFEX


class wsfex_currency_codes(models.Model):
    _name = "wsfex.currency.codes"
    _description = "WSFEX Currency Codes"
    _order = 'code'

    code = fields.Char('Code', required=True, size=4)
    name = fields.Char('Desc', required=True, size=64)
    currency_id = fields.Many2one('res.currency', string="OpenERP Currency")
    wsfex_config_id = fields.Many2one('wsfex.config')


class wsfex_uom_codes(models.Model):
    _name = "wsfex.uom.codes"
    _description = "WSFEX UoM Codes"
    _order = 'code'

    code = fields.Integer('Code', required=True)
    name = fields.Char('Desc', required=True, size=64)
    uom_id = fields.Many2one('product.uom', string="OpenERP UoM")
    wsfex_config_id = fields.Many2one('wsfex.config')


class wsfex_lang_codes(models.Model):
    _name = "wsfex.lang.codes"
    _description = "WSFEX Language Codes"
    _order = 'code'

    code = fields.Integer('Code', required=True)
    name = fields.Char('Desc', required=True, size=64)
    lang_id = fields.Many2one('res.lang', string="OpenERP Language")
    wsfex_config_id = fields.Many2one('wsfex.config')


class wsfex_dst_country_codes(models.Model):
    _name = "wsfex.dst_country.codes"
    _description = "WSFEX Dest Country Codes"
    _order = 'name'

    code = fields.Char('Code', size=3, required=True)
    name = fields.Char('Desc', required=True, size=64)
    country_id = fields.Many2one('res.country', string="OpenERP Country")
    wsfex_config_id = fields.Many2one('wsfex.config')


class wsfex_incoterms_codes(models.Model):
    _name = "wsfex.incoterms.codes"
    _description = "WSFEX Incoterms Codes"
    _order = 'code'

    code = fields.Char('Code', size=5, required=True)
    name = fields.Char('Desc', required=True, size=64)
    incoterms_id = fields.Many2one('stock.incoterms', string="OpenERP Incoterm")
    wsfex_config_id = fields.Many2one('wsfex.config')


class wsfex_dst_cuit_codes(models.Model):
    _name = "wsfex.dst_cuit.codes"
    _description = "WSFEX DST CUIT Codes"
    _order = 'name'

    code = fields.Float('Code', digits=(12, 0), required=True)
    name = fields.Char('Desc', required=True, size=64)
    wsfex_config_id = fields.Many2one('wsfex.config')


class wsfex_export_type_codes(models.Model):
    _name = "wsfex.export_type.codes"
    _description = "WSFEX Export Type Codes"
    _order = 'code'

    code = fields.Integer('Code', required=True)
    name = fields.Char('Desc', required=True, size=64)
    wsfex_config_id = fields.Many2one('wsfex.config')


class wsfex_voucher_type_codes(models.Model):
    _name = "wsfex.voucher_type.codes"
    _description = "WSFEX Voucher Type Codes"
    _order = 'code'

    code = fields.Integer('Code', required=True)
    name = fields.Char('Desc', required=True, size=64)
    voucher_type_id = fields.Many2one('wsfe.voucher_type', string="OpenERP Voucher Type")
    wsfex_config_id = fields.Many2one('wsfex.config')


class NoAttErr(object):

    def __init__(self, voucher_res):
        self.voucher_res = voucher_res

    def __getattr__(self, item):
        try:
            return getattr(self.voucher_res, item)
        except AttributeError:
            return False


class WsfexConfig(models.Model):
    _name = "wsfex.config"
    _description = "Configuration for WSFEX"

    name = fields.Char('Name', size=64, required=True)
    cuit = fields.Char(related='company_id.partner_id.vat', string='Cuit')
    url = fields.Char('URL for WSFEX', size=60, required=True)
    homologation = fields.Boolean('Homologation', default=False,
                                  help="If true, there will be some validations that are disabled,"
                                  " for example, invoice number correlativeness")
    point_of_sale_ids = fields.Many2many('pos.ar', 'pos_ar_wsfex_rel', 'wsfex_config_id',
                                         'pos_ar_id', 'Points of Sale')
    wsaa_ticket_id = fields.Many2one('wsaa.ta', 'Ticket Access')
    currency_ids = fields.One2many('wsfex.currency.codes', 'wsfex_config_id', 'Currencies')
    uom_ids = fields.One2many('wsfex.uom.codes', 'wsfex_config_id', 'Units of Measure')
    lang_ids = fields.One2many('wsfex.lang.codes', 'wsfex_config_id', 'Languages')
    country_ids = fields.One2many('wsfex.dst_country.codes', 'wsfex_config_id', 'Countries')
    incoterms_ids = fields.One2many('wsfex.incoterms.codes', 'wsfex_config_id', 'Incoterms')
    dst_cuit_ids = fields.One2many('wsfex.dst_cuit.codes', 'wsfex_config_id', 'DST CUIT')
    voucher_type_ids = fields.One2many('wsfex.voucher_type.codes', 'wsfex_config_id',
                                       'Voucher Type')
    export_type_ids = fields.One2many('wsfex.export_type.codes', 'wsfex_config_id', 'Export Type')
    company_id = fields.Many2one('res.company', 'Company Name', required=True,
                                 default=lambda o: o.env.user.company_id.id)

    @api.model
    def create(self, vals):
        """Extend to add a wsaa_ticket_id if not provided."""

        if vals.get("wsaa_ticket_id"):
            return super(WsfexConfig, self).create(vals)

        # Buscamos primero el wsaa que corresponde a esta compania
        # porque hay que recordar que son unicos por compania
        wsaa_obj = self.env['wsaa.config']
        service_obj = self.env['afipws.service']
        wsaa_ids = wsaa_obj.search([('company_id', '=', vals['company_id'])]).ids
        service_ids = service_obj.search([('name', '=', 'wsfex')]).ids
        if wsaa_ids:
            # Creamos tambien un TA para este servcio y esta compania
            ta_vals = {
                'name': service_ids[0],
                'company_id': vals['company_id'],
                'config_id': wsaa_ids[0],
            }
            ta_obj = self.env['wsaa.ta']
            ta_id = ta_obj.create(ta_vals).id
            vals['wsaa_ticket_id'] = ta_id

        return super(WsfexConfig, self).create(vals)

    def get_config(self, pos_ar=None, raise_err=True):
        # Obtenemos la compania que esta utilizando en este momento este usuario
        company_id = self.env.user.company_id.id
        if not company_id and raise_err:
            raise exceptions.ValidationError(_('There is no company being used by this user'))

        search_domain = [('company_id', '=', company_id)]
        if pos_ar:
            search_domain.append(('point_of_sale_ids', 'in', pos_ar.id))

        ids = self.search(search_domain)
        if raise_err:
            # More than one valid configuration found
            if len(ids) > 1:
                raise exceptions.ValidationError(
                    _("There is more than one configuration with this POS %s") % pos_ar.name)
            # No valid configuration found
            elif not ids:
                raise exceptions.ValidationError(
                    _('There is no WSFEX configuration set to this company'))

        return ids

    def check_error(self, response, raise_exception=True):
        msg = ''
        if 'error' in response and raise_exception:
            error = response['error'].msg
            err_code = str(response['error'].code)
            msg = _('WSFE Error!\n\nCode: %s\n\nError: %s') % (error, err_code)
            raise exceptions.ValidationError(msg)

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

    def fetch_response(self, service):
        """Ping `service` to get the required data. Raises an exception if the response is not
        valid."""

        _wsfex = self.build_wsfex_service()
        res = _wsfex.FEXGetPARAM(service)
        self.check_error(res)
        #self.check_event(res)
        return res

    def make_request(self, service, code_key, name_key):
        # Armo un lista con los codigos de los Impuestos
        res = self.fetch_response(service)
        for r in res['response'][0]:
            # El servicio de AFIP me devuelve dentro de la lista
            # unos valores None
            if not r:
                continue

            code = code_key(r)
            name = name_key(r)
            yield code, name, r

    @api.multi
    def get_wsfex_currencies(self):
        wsfex_param_obj = self.env['wsfex.currency.codes']
        for wsfex_obj in self:
            ref_id = wsfex_obj.id
            for code, name, __ in wsfex_obj.make_request(
                service="MON",
                code_key=attrgetter("Mon_Id"),
                name_key=attrgetter("Mon_Ds"),
            ):
                res_c = wsfex_param_obj.search([('code', '=', code)])
                # Si los codigos estan en la db los modifico
                if res_c:
                    res_c.write({'name': name, 'wsfex_config_id': ref_id})
                # Si no tengo los codigos de esos Impuestos en la db, los creo
                else:
                    wsfex_param_obj.create({'code': code, 'name': name, 'wsfex_config_id': ref_id})

        return True

    @api.multi
    def get_wsfex_uoms(self):
        wsfex_param_obj = self.env['wsfex.uom.codes']
        for wsfex_obj in self:
            ref_id = wsfex_obj.id
            for code, name, __ in wsfex_obj.make_request(
                service="UMed",
                code_key=attrgetter("Umed_Id"),
                name_key=attrgetter("Umed_Ds"),
            ):
                res_c = wsfex_param_obj.search([('code', '=', code)])
                # Si los codigos estan en la db los modifico
                if res_c:
                    res_c.write({'name': name, 'wsfex_config_id': ref_id})
                # Si no tengo los codigos de esos Impuestos en la db, los creo
                else:
                    wsfex_param_obj.create({'code': code, 'name': name, 'wsfex_config_id': ref_id})

        return True

    @api.multi
    def get_wsfex_langs(self):
        wsfex_param_obj = self.env['wsfex.lang.codes']
        for wsfex_obj in self:
            ref_id = wsfex_obj.id
            for code, name, __ in wsfex_obj.make_request(
                service="Idiomas",
                code_key=attrgetter("Idi_Id"),
                name_key=attrgetter("Idi_Ds"),
            ):
                res_c = wsfex_param_obj.search([('code', '=', code)])
                # Si los codigos estan en la db los modifico
                if res_c:
                    res_c.write({'name': name, 'wsfex_config_id': ref_id})
                # Si no tengo los codigos de esos Impuestos en la db, los creo
                else:
                    wsfex_param_obj.create({'code': code, 'name': name, 'wsfex_config_id': ref_id})

        return True

    @api.multi
    def get_wsfex_export_types(self):
        wsfex_param_obj = self.env['wsfex.export_type.codes']
        for wsfex_obj in self:
            ref_id = wsfex_obj.id
            for code, name, __ in wsfex_obj.make_request(
                service="Tipo_Expo",
                code_key=attrgetter("Tex_Id"),
                name_key=attrgetter("Tex_Ds"),
            ):
                res_c = wsfex_param_obj.search([('code', '=', code)])
                # Si los codigos estan en la db los modifico
                if res_c:
                    res_c.write({'name': name, 'wsfex_config_id': ref_id})
                # Si no tengo los codigos de esos Impuestos en la db, los creo
                else:
                    wsfex_param_obj.create({'code': code, 'name': name, 'wsfex_config_id': ref_id})

        return True

    @api.multi
    def get_wsfex_countries(self):
        wsfex_param_obj = self.env['wsfex.dst_country.codes']
        country_model = self.env["res.country"]
        do_create = self.env.context.get("force_create_country", True)
        for wsfex_obj in self:
            ref_id = wsfex_obj.id
            for code, name, __ in wsfex_obj.make_request(
                service="DST_pais",
                code_key=attrgetter("DST_Codigo"),
                name_key=attrgetter("DST_Ds"),
            ):
                res_c = wsfex_param_obj.search([('code', '=', code)])
                country_id = country_model.get_or_create_country_for_wsfex(
                    name, do_create=do_create).id
                # Si los codigos estan en la db los modifico
                if res_c:
                    res_c.write({'name': name, 'wsfex_config_id': ref_id,
                                 "country_id": country_id})
                # Si no tengo los codigos de esos Impuestos en la db, los creo
                else:
                    wsfex_param_obj.create({'code': code, 'name': name, 'wsfex_config_id': ref_id,
                                            "country_id": country_id})

        return True

    @api.multi
    def get_wsfex_incoterms(self):
        wsfex_param_obj = self.env['wsfex.incoterms.codes']
        for wsfex_obj in self:
            ref_id = wsfex_obj.id
            for code, name, __ in wsfex_obj.make_request(
                service="Incoterms",
                code_key=attrgetter("Inc_Id"),
                name_key=attrgetter("Inc_Ds"),
            ):
                res_c = wsfex_param_obj.search([('code', '=', code)])
                # Si los codigos estan en la db los modifico
                if res_c:
                    res_c.write({'name': name, 'wsfex_config_id': ref_id})
                # Si no tengo los codigos de esos Impuestos en la db, los creo
                else:
                    wsfex_param_obj.create({'code': code, 'name': name, 'wsfex_config_id': ref_id})
        return True

    @api.multi
    def get_wsfex_dst_cuits(self):
        wsfex_param_obj = self.env['wsfex.dst_cuit.codes']
        for wsfex_obj in self:
            ref_id = wsfex_obj.id
            for code, name, __ in wsfex_obj.make_request(
                service="DST_CUIT",
                code_key=attrgetter("DST_CUIT"),
                name_key=attrgetter("DST_Ds"),
            ):
                res_c = wsfex_param_obj.search([('code', '=', code)])
                # Si los codigos estan en la db los modifico
                if res_c:
                    res_c.write({'name': name, 'wsfex_config_id': ref_id})
                # Si no tengo los codigos de esos Impuestos en la db, los creo
                else:
                    wsfex_param_obj.create({'code': code, 'name': name, 'wsfex_config_id': ref_id})

        return True

    @api.multi
    def get_wsfex_voucher_types(self):
        wsfex_param_obj = self.env['wsfex.voucher_type.codes']
        for wsfex_obj in self:
            ref_id = wsfex_obj.id
            for code, name, __ in wsfex_obj.make_request(
                service="Cbte_Tipo",
                code_key=attrgetter("Cbte_Id"),
                name_key=attrgetter("Cbte_Ds"),
            ):
                res_c = wsfex_param_obj.search([('code', '=', code)])
                # Si los codigos estan en la db los modifico
                if res_c:
                    res_c.write({'name': name, 'wsfex_config_id': ref_id})
                # Si no tengo los codigos de esos Impuestos en la db, los creo
                else:
                    wsfex_param_obj.create({'code': code, 'name': name, 'wsfex_config_id': ref_id})

        return True

    def build_wsfex_service(self):
        conf = self
        token, sign = conf.wsaa_ticket_id.get_token_sign()
        _wsfex = WSFEX(conf.cuit, token, sign, conf.url)
        return _wsfex

    @api.multi
    def get_invoice_CAE(self, pos, voucher_type, details):
        _wsfex = self.build_wsfex_service()
        # Agregamos la info que falta
        details['Cbte_Tipo'] = voucher_type
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
#            doc_num = comp['Cuit'] == int(inv.partner_id.vat)
            #cbte = True
            if inv.internal_number:
                #cbte =
                comp['Cbte_nro'] == int(inv.internal_number.split('-')[1])
            else:
                # TODO: El nro de factura deberia unificarse para que se setee en una funcion
                # o algo asi para que no haya posibilidad de que sea diferente nunca en su formato
                invoice_vals['internal_number'] = '%04d-%08d' % (result['PtoVta'],
                                                                 comp['CbteHasta'])

#            if not all([cbte]):
#                raise osv.except_osv(_("WSFE Error!"),
#                                     _("Validated invoice that not corresponds!"))

            invoice_vals['cae'] = comp['Cae']
            invoice_vals['cae_due_date'] = comp['Fch_venc_Cae']
            invoices_approbed[inv.id] = invoice_vals

        return invoices_approbed

    # TODO: Migrar a v8
    def _log_wsfe_request(self, cr, uid, ids, pos, voucher_type_code, detail, res, context=None):

        wsfex_req_obj = self.pool.get('wsfex.request.detail')
        voucher_type_obj = self.pool.get('wsfe.voucher_type')
        voucher_type_ids = voucher_type_obj.search(cr, uid, [('code', '=', voucher_type_code)])
        #voucher_type_name = voucher_type_obj.read(cr, uid, voucher_type_ids, ['name'])[0]['name']

        error = 'error' in res

        # Esto es para fixear un bug que al hacer un refund, si fallaba algo con la AFIP
        # se hace el rollback por lo tanto el refund que se estaba creando ya no existe en
        # base de datos y estariamos violando una foreign key contraint. Por eso,
        # chequeamos que existe info de la invoice_id, sino lo seteamos en False
        read_inv = self.pool.get('account.invoice').read(
            cr, uid, detail['invoice_id'], ['id', 'internal_number'], context=context)

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

    def get_last_voucher(self, pos, voucher_type):
        _wsfex = self.build_wsfex_service()
        res = _wsfex.FEXGetLast_CMP(pos, voucher_type)
        self.check_error(res)
        self.check_event(res)
        last = res['response']
        return last

    @api.model
    def get_voucher_info(self, pos, voucher_type, number):
        _wsfex = self.build_wsfex_service()
        res = _wsfex.fe_comp_consultar(pos, voucher_type, number)

        self.check_error(res)
        self.check_event(res)
        #last = res['response'].CbteNro

        res = res['response']
        voucher_res = NoAttErr(res[0])
        result = {
            'Id': voucher_res.Id,
            'Fecha_cbte': voucher_res.Fecha_cbte,
            'Cbte_tipo': voucher_res.Cbte_tipo,
            'Punto_vta': voucher_res.Punto_vta,
            'Cbte_nro': voucher_res.Cbte_nro,
            'Tipo_expo': voucher_res.Tipo_expo,
            'Permiso_existente': voucher_res.Permiso_existente,
            'Permisos': voucher_res.Permisos,
            'Dst_cmp': voucher_res.Dst_cmp,
            'Cliente': voucher_res.Cliente,
            'Cuit_pais_cliente': voucher_res.Cuit_pais_cliente,
            'Domicilio_cliente': voucher_res.Domicilio_cliente,
            'Id_impositivo': voucher_res.Id_impositivo,
            'Moneda_Id': voucher_res.Moneda_Id,
            'Moneda_ctz': voucher_res.Moneda_ctz,
            'Obs_comerciales': voucher_res.Obs_comerciales,
            'Imp_total': voucher_res.Imp_total,
            'Obs': voucher_res.Obs,
            'Forma_pago': voucher_res.Forma_pago,
            'Incoterms': voucher_res.Incoterms,
            'Incoterms_Ds': voucher_res.Incoterms_Ds,
            'Idioma_cbte': voucher_res.Idioma_cbte,
            'Items': voucher_res.Items,
            'Fecha_cbte_cae': voucher_res.Fecha_cbte_cae,
            'Fch_venc_Cae': voucher_res.Fch_venc_Cae,
            'Cae': voucher_res.Cae,
            'Resultado': voucher_res.Resultado,
            'Motivos_Obs': voucher_res.Motivos_Obs,
            'Fecha_pago': voucher_res.Fecha_pago,
            'Cmps_asoc': voucher_res.Cmps_asoc,
        }

        return result

    def prepare_details(self, invoices):
        company = self.env.user.company_id
        voucher_type_obj = self.env['wsfe.voucher_type']
        currency_code_obj = self.env['wsfex.currency.codes']
        uom_code_obj = self.env['wsfex.uom.codes']

        if len(invoices) > 1:
            raise exceptions.ValidationError(
                _("You cannot inform more than one invoice to AFIP WSFEX"))

        first_num = self._context.get('first_num', False)
        Id = int(datetime.strftime(datetime.now(), '%Y%m%d%H%M%S'))
        cbte_nro = 0

        Cmp = None
        for inv in invoices:

            # Obtenemos el numero de comprobante a enviar a la AFIP teniendo en
            # cuenta que inv.number == 000X-00000NN o algo similar.
            if not inv.internal_number:
                if not first_num:
                    raise osv.except_osv(_("WSFE Error!"),
                                         _("There is no first invoice number declared!"))
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

            cuit_pais = inv.dst_cuit_id and int(inv.dst_cuit_id.code) or 0
            inv_currency_id = inv.currency_id.id
            curr_codes = currency_code_obj.search([('currency_id', '=', inv_currency_id)])

            if curr_codes:
                curr_code = curr_codes[0].code
                curr_rate = company.currency_id.id == inv_currency_id and 1.0 or inv.currency_rate
            else:
                raise exceptions.ValidationError(
                    _("Currency %s has not code configured") % inv.currency_id.name)

            # Items
            items = []
            for i, line in enumerate(inv.invoice_line):
                uom_id = line.uos_id.id
                uom_codes = uom_code_obj.search([('uom_id','=',uom_id)])
                if not uom_codes:
                    raise osv.except_osv(_("WSFEX Error!"), _("There is no UoM Code defined for %s in line %s") % (line.uos_id.name, line.name))

                uom_code = uom_codes[0].code

                items.append({
                    'Pro_codigo' : i,
                    'Pro_ds' : line.name.encode('ascii', errors='ignore'),
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
                Cmp_asoc = {'Cmp_asoc': {
                    'Cbte_tipo': tipo_cbte,
                    'Cbte_punto_vta': int(pos),
                    'Cbte_nro': int(number),
                }}

                Cmps_asoc.append(Cmp_asoc)

            cbte_tipo = voucher_type_obj.get_voucher_type(inv)
            if cbte_tipo in ('20', '21'):
                formatted_date_invoice = ''

            Cmp = {
                'invoice_id': inv.id,
                'Id': Id,
                'Cbte_Tipo': cbte_tipo,
                'Fecha_cbte': formatted_date_invoice,
                #'Punto_vta': pto_venta,
                'Cbte_nro': cbte_nro,
                'Tipo_expo': inv.export_type_id.code,  # Exportacion de bienes
                'Dst_cmp': inv.dst_country_id.code,
                'Cliente': inv.partner_id.name.encode('ascii', errors='ignore'),
                'Domicilio_cliente': inv.partner_id.contact_address.encode('ascii',
                                                                           errors='ignore'),
                'Cuit_pais_cliente': cuit_pais,
                'Id_impositivo': inv.partner_id.vat,
                'Moneda_Id': curr_code,
                'Moneda_ctz': curr_rate,
                'Imp_total': inv.amount_total,
                'Idioma_cbte': 1,
                'Items': items,
            }

            # Datos No Obligatorios
            if inv.incoterm_id:
                Cmp['Incoterms'] = inv.incoterm_id.code
                Cmp['Incoterms_Ds'] = inv.incoterm_id.name

            if Cmps_asoc:
                Cmp['Cmps_asoc'] = Cmps_asoc

        return Cmp
