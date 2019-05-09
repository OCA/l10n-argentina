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
#    it under the terms of the GNU Affero General
#    Public License as published by
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

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.l10n_ar_wsfe.wsfetools.wsfex_suds import WSFEX as wsfex
from datetime import datetime


class WsfexShippingPermission(models.Model):
    _name = "wsfex.shipping.permission"
    _description = "WSFEX Shipping Permission"

    name = fields.Char('Code', required=True, size=16)
    invoice_id = fields.Many2one('account.invoice', 'Invoice')
    dst_country_id = fields.Many2one('wsfex.dst_country.codes',
                                     'Dest Country', required=True)


class WsfexCurrencyCodes(models.Model):
    _name = "wsfex.currency.codes"
    _description = "WSFEX Currency Codes"
    _order = 'code'

    code = fields.Char('Code', required=True, size=4)
    name = fields.Char('Desc', required=True, size=64)
    currency_id = fields.Many2one('res.currency', string="OpenERP Currency")
    wsfex_config_id = fields.Many2one('wsfex.config')


class WsfexUomCodes(models.Model):
    _name = "wsfex.uom.codes"
    _description = "WSFEX UoM Codes"
    _order = 'code'

    code = fields.Integer('Code', required=True)
    name = fields.Char('Desc', required=True, size=64)
    uom_id = fields.Many2one('product.uom', string="OpenERP UoM")
    wsfex_config_id = fields.Many2one('wsfex.config')


class WsfexLangCodes(models.Model):
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
    incoterms_id = fields.Many2one(comodel_name='stock.incoterms',
                                   string="OpenERP Incoterm")
    wsfex_config_id = fields.Many2one('wsfex.config')


class DstCuitCodes(models.Model):
    _inherit = "dst_cuit.codes"

    wsfex_config_id = fields.Many2one('wsfex.config')


class WsfexExportTypeCodes(models.Model):
    _name = "wsfex.export_type.codes"
    _description = "WSFEX Export Type Codes"
    _order = 'code'

    code = fields.Integer('Code', required=True)
    name = fields.Char('Desc', required=True, size=64)
    wsfex_config_id = fields.Many2one('wsfex.config')


class WsfexVoucherTypeCodes(models.Model):
    _name = "wsfex.voucher_type.codes"
    _description = "WSFEX Voucher Type Codes"
    _order = 'code'

    code = fields.Integer('Code', required=True)
    name = fields.Char('Desc', required=True, size=64)
    voucher_type_id = fields.Many2one(comodel_name='wsfe.voucher_type',
                                      string="OpenERP Voucher Type")
    wsfex_config_id = fields.Many2one('wsfex.config')


class WsfexConfig(models.Model):
    _name = "wsfex.config"
    _description = "Configuration for WSFEX"

    name = fields.Char('Name', size=64, required=True)
    cuit = fields.Char(related='company_id.partner_id.vat', string='Cuit')
    url = fields.Char('URL for WSFEX', size=60, required=True)
    homologation = fields.Boolean(
        comodel_name='Homologation',
        default=False,
        help="If true, there will be some validations that are \
        disabled, for example, invoice number correlativeness")
    point_of_sale_ids = fields.Many2many('pos.ar', 'pos_ar_wsfex_rel',
                                         'wsfex_config_id', 'pos_ar_id',
                                         'Points of Sale')
    wsaa_ticket_id = fields.Many2one('wsaa.ta', 'Ticket Access')
    currency_ids = fields.One2many(comodel_name='wsfex.currency.codes',
                                   inverse_name='wsfex_config_id',
                                   string='Currencies')
    uom_ids = fields.One2many(comodel_name='wsfex.uom.codes',
                              inverse_name='wsfex_config_id',
                              string='Units of Measure')
    lang_ids = fields.One2many(comodel_name='wsfex.lang.codes',
                               inverse_name='wsfex_config_id',
                               string='Languages')
    country_ids = fields.One2many(comodel_name='wsfex.dst_country.codes',
                                  inverse_name='wsfex_config_id',
                                  string='Countries')
    incoterms_ids = fields.One2many(comodel_name='wsfex.incoterms.codes',
                                    inverse_name='wsfex_config_id',
                                    string='Incoterms')
    dst_cuit_ids = fields.One2many(comodel_name='dst_cuit.codes',
                                   inverse_name='wsfex_config_id',
                                   string='DST CUIT')
    voucher_type_ids = fields.One2many(comodel_name='wsfex.voucher_type.codes',
                                       inverse_name='wsfex_config_id',
                                       string='Voucher Type')
    export_type_ids = fields.One2many(comodel_name='wsfex.export_type.codes',
                                      inverse_name='wsfex_config_id',
                                      string='Export Type')
    company_id = fields.Many2one(comodel_name='res.company',
                                 string='Company Name',
                                 default=lambda self: self.
                                 env['res.users']._get_company(),
                                 required=True)

    _sql_constraints = [
        # ('company_uniq', 'unique (company_id)',
        #  'The configuration must be unique per company !')
    ]

    _defaults = {
        # 'company_id': lambda self, cr, uid, context=None:
        # self.env['res.users']._get_company(cr, uid, context=context),
    }

    @api.model
    def create(self, vals):
        # Creamos tambien un TA para este servcio y esta compania
        ta_obj = self.env['wsaa.ta']
        wsaa_obj = self.env['wsaa.config']
        service_obj = self.env['afipws.service']

        # Buscamos primero el wsaa que corresponde a esta compania
        # porque hay que recordar que son unicos por compania
        wsaa = wsaa_obj.search([('company_id', '=', vals['company_id'])])
        service = service_obj.search([('name', '=', 'wsfex')])
        if wsaa:
            ta_vals = {
                'name': service.id,
                'company_id': vals['company_id'],
                'config_id': wsaa.id,
                }

            ta = ta_obj.create(ta_vals)
            vals['wsaa_ticket_id'] = ta.id

        return super(WsfexConfig, self).create(vals)

    @api.multi
    def unlink(self):
        for wsfex_conf in self:
            wsfex_conf.wsaa_ticket_id.unlink()
        res = super(WsfexConfig, self).unlink()
        return res

    def get_config(self):
        company_id = self._context.company_id
        without_raise = self.env.context.get('without_raise', False)
        if not company_id and not without_raise:
            raise UserError(
                _('Company Error!\n') +
                _('There is no company being used by this user'))

        ids = self.search([('company_id', '=', company_id)])
        if not ids and not without_raise:
            raise UserError(
                _('WSFEX Config Error!\n') +
                _('There is no WSFEX configuration set to this company'))

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
            res_c = wsfex_cur_obj.search([('code', '=', r.Mon_Id)])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_cur_obj.create({
                    'code': r.Mon_Id,
                    'name': r.Mon_Ds,
                    'wsfex_config_id': self.id,
                })
            # Si los codigos estan en la db los modifico
            else:
                res_c.write({
                    'name': r.Mon_Ds,
                    'wsfex_config_id': self.id,
                })

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
            res_c = wsfex_uom_obj.search([('code', '=', r.Umed_Id)])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_uom_obj.create({
                    'code': r.Umed_Id,
                    'name': r.Umed_Ds,
                    'wsfex_config_id': self.id,
                })
            # Si los codigos estan en la db los modifico
            else:
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
            res_c = wsfex_param_obj.search([('code', '=', r.Idi_Id)])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create({
                    'code': r.Idi_Id,
                    'name': r.Idi_Ds,
                    'wsfex_config_id': self.id,
                })
            # Si los codigos estan en la db los modifico
            else:
                res_c.write({'name': r.Idi_Ds, 'wsfex_config_id': self.id})

        return True

    @api.multi
    def get_wsfex_export_types(self):
        self.ensure_one()
        conf = self

        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfex = wsfex(self.cuit, token, sign, self.url)
        res = _wsfex.FEXGetPARAM("Tipo_Expo")

        wsfex_param_obj = self.env['wsfex.export_type.codes']

        # Chequeamos los errores
        # msg = self.check_errors(cr, uid, res,
        #                         raise_exception=False, context=context)
        # if msg:
        #     # TODO: Hacer un wrapping de los errores, porque algunos son
        #     # largos y se imprimen muy mal en pantalla
        #     raise UserError(_('Error reading taxes'), msg)

        # Armo un lista con los codigos de los Impuestos
        for r in res['response'][0]:
            # El servicio de AFIP me devuelve dentro de la lista
            # unos valores None
            if not r:
                continue
            res_c = wsfex_param_obj.search([('code', '=', r.Tex_Id)])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create({
                    'code': r.Tex_Id,
                    'name': r.Tex_Ds,
                    'wsfex_config_id': self.id,
                })
            # Si los codigos estan en la db los modifico
            else:
                res_c.write({'name': r.Tex_Ds, 'wsfex_config_id': self.id})
        return True

    @api.multi
    def get_wsfex_countries(self):
        self.ensure_one()
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
            res_c = wsfex_param_obj.search([('code', '=', r.DST_Codigo)])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create({
                    'code': r.DST_Codigo,
                    'name': r.DST_Ds,
                    'wsfex_config_id': self.id,
                })
            # Si los codigos estan en la db los modifico
            else:
                res_c.write({'name': r.DST_Ds, 'wsfex_config_id': self.id})

        return True

    @api.multi
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
            res_c = wsfex_param_obj.search([('code', '=', r.Inc_Id)])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                wsfex_param_obj.create({
                    'code': r.Inc_Id,
                    'name': r.Inc_Ds,
                    'wsfex_config_id': self.id,
                })
            # Si los codigos estan en la db los modifico
            else:
                res_c.write({'name': r.Inc_Ds, 'wsfex_config_id': self.id})

        return True

    @api.multi
    def get_wsfex_dst_cuits(self):
        self.ensure_one()
        conf = self

        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfex = wsfex(self.cuit, token, sign, self.url)
        res = _wsfex.FEXGetPARAM("DST_CUIT")

        param_obj = self.env['dst_cuit.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res['response'][0]:
            # El servicio de AFIP me devuelve dentro de la lista
            # unos valores None
            if not r:
                continue
            res_c = param_obj.search([('code', '=', r.DST_CUIT)])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                param_obj.create({
                    'code': r.DST_CUIT,
                    'name': r.DST_Ds,
                    'wsfex_config_id': self.id,
                })
            # Si los codigos estan en la db los modifico
            else:
                res_c.write({'name': r.DST_Ds, 'wsfex_config_id': self.id})

        return True

    @api.multi
    def get_wsfex_voucher_types(self):
        self.ensure_one()
        conf = self

        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfex = wsfex(self.cuit, token, sign, self.url)
        param_func = "Tipo_Cbte"
        res = _wsfex.FEXGetPARAM(param_func)

        wsfex_param_obj = self.env['wsfex.voucher_type.codes']
        # Armo un lista con los codigos de los Impuestos
        for r in res['response'][0]:
            # El servicio de AFIP me devuelve dentro de la lista
            # unos valores None
            if not r:
                continue
            res_c = wsfex_param_obj.search([('code', '=', r.Cbte_Id)])

            # Si no tengo los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                vals = {
                    'code': r.Cbte_Id,
                    'name': r.Cbte_Ds,
                    'wsfex_config_id': self.id
                }
                wsfex_param_obj.create(vals)
            # ~ Si los codigos estan en la db los modifico
            else:
                vals = {
                    'name': r.Cbte_Ds,
                    'wsfex_config_id': self.id
                }
                res_c.write(vals)

        return True

    def check_error(self, res, raise_exception=True):
        msg = ''
        if 'error' in res:
            error = res['error'].msg
            err_code = str(res['error'].code)
            msg = 'Codigo/s Error: %s[%s]' % (error, err_code)

            if msg != '' and raise_exception:
                raise UserError(_('WSFE Error!\n') + msg)

        return msg

    def check_event(self, res):
        msg = ''
        if 'event' in res:
            event = res['event'].msg
            eve_code = str(res['event'].code)
            msg = 'Codigo/s Observacion: %s [%s]' % (event, eve_code)

            # TODO: Donde lo ponemos a esto?
            # Escribimos en el log del cliente web
            # self.log(cr, uid, None, msg, context)

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
                raise UserError(_('AFIP Web Service Error\n') +
                                _('La factura no fue aprobada. \n%s') % msg)

        # Igualmente, siempre va a ser una para FExp
        for inv in invoices:
            invoice_vals = {}

            comp = result['response']

            # Chequeamos que se corresponda con la
            # factura que enviamos a validar
            # doc_num = comp['Cuit'] == int(inv.partner_id.vat)
            # cbte = True
            # if inv.internal_number:
            #     cbte = comp['Cbte_nro'] == int(
            #         inv.internal_number.split('-')[1])
            # else:
            if not inv.internal_number:
                # TODO: El nro de factura deberia unificarse para que
                # se setee en una funcion o algo asi para que no haya
                # posibilidad de que sea diferente nunca en su formato
                invoice_vals['internal_number'] = '%04d-%08d' % \
                    (result['PtoVta'], comp['CbteHasta'])

            # if not all([cbte]):
            #     raise UserError(
            #         _("WSFE Error!") +
            #         _("Validated invoice that not corresponds!"))

            invoice_vals['cae'] = comp['Cae']
            invoice_vals['cae_due_date'] = comp['Fch_venc_Cae']
            invoices_approbed[inv.id] = invoice_vals

        return invoices_approbed

    @api.multi
    def _log_wsfe_request(self, pos, voucher_type_code, detail, res):

        wsfex_req_obj = self.env['wsfex.request.detail']
        voucher_type_obj = self.env['wsfe.voucher_type']
        voucher_types = voucher_type_obj.search(
            [('code', '=', voucher_type_code)])

        error = 'error' in res

        # Esto es para fixear un bug que al hacer un refund, si fallaba algo
        # con la AFIP se hace el rollback por lo tanto el refund que
        # se estaba creando ya no existe en base de datos y estariamos
        # violando una foreign key contraint. Por eso, chequeamos que existe
        # info de la invoice_id, sino lo seteamos en False
        inv = self.env['account.invoice'].browse(detail['invoice_id'])
        read_inv = inv.read(['id', 'internal_number'])

        if not read_inv:
            invoice_id = False
        else:
            invoice_id = detail['invoice_id']

        vals = {
            'invoice_id': invoice_id,
            'request_id': detail['Id'],
            'voucher_number': '%04d-%08d' % (pos, detail['Cbte_nro']),
            'voucher_type_id': voucher_types.ids[0],
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

        return wsfex_req_obj.create(vals)

    @api.multi
    def get_last_voucher(self, pos, voucher_type):
        conf = self

        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfe = wsfex(conf.cuit, token, sign, conf.url)
        res = _wsfe.FEXGetLast_CMP(pos, voucher_type)

        self.check_error(res)
        self.check_event(res)
        last = res['response']
        return last

    @api.multi
    def prepare_details(self, invoices):
        company = self.env.user.company_id
        voucher_type_obj = self.env['wsfe.voucher_type']
        currency_code_obj = self.env['wsfex.currency.codes']
        uom_code_obj = self.env['wsfex.uom.codes']

        if len(invoices) > 1:
            raise UserError(
                _("WSFEX Error!\n") +
                _("You cannot inform more than one invoice to AFIP WSFEX"))

        first_num = self._context.get('first_num', False)
        Id = int(datetime.strftime(datetime.now(), '%Y%m%d%H%M%S'))
        cbte_nro = 0

        for inv in invoices:

            # Obtenemos el numero de comprobante a enviar a la AFIP teniendo en
            # cuenta que inv.number == 000X-00000NN o algo similar.
            if not inv.internal_number:
                if not first_num:
                    raise UserError(
                        _("WSFE Error!\n") +
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
            curr_codes = currency_code_obj.search(
                [('currency_id', '=', inv_currency_id)])

            if curr_codes:
                curr_code = curr_codes[0].code
                curr_rate = company.currency_id.id == inv_currency_id and \
                    1.0 or inv.currency_rate
            else:
                raise UserError(
                    _("WSFEX Error!\n") +
                    _("Currency %s has not code configured") %
                    inv.currency_id.name)

            # Items
            items = []
            for i, line in enumerate(inv.invoice_line_ids):
                uom_id = line.uos_id.id
                uom_codes = uom_code_obj.search([('uom_id', '=', uom_id)])
                if not uom_codes:
                    raise UserError(
                        _("WSFEX Error!\n") +
                        _("There is no UoM Code defined for %s in line %s")
                        % (line.uos_id.name, line.name))

                uom_code = uom_codes[0].code

                items.append({
                    'Pro_codigo': i,  # product_code,
                    'Pro_ds': line.name.encode('ascii', errors='ignore'),
                    'Pro_qty': line.quantity,
                    'Pro_umed': uom_code,
                    'Pro_precio_uni': line.price_unit,
                    'Pro_total_item': line.price_subtotal,
                    'Pro_bonificacion': 0,
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

            # TODO: Agregar permisos
            shipping_perm = 'S' and inv.shipping_perm_ids or 'N'

            Cmp = {
                'invoice_id': inv.id,
                'Id': Id,
                # 'Tipo_cbte': cbte_tipo,
                'Fecha_cbte': formatted_date_invoice,
                # 'Punto_vta': pto_venta,
                'Cbte_nro': cbte_nro,
                'Tipo_expo': inv.export_type_id.code,  # Exportacion de bienes
                'Permiso_existente': shipping_perm,
                'Dst_cmp': inv.dst_country_id.code,
                'Cliente': inv.partner_id.name.encode('ascii',
                                                      errors='ignore'),
                'Domicilio_cliente': inv.partner_id.contact_address.encode(
                    'ascii', errors='ignore'),
                'Cuit_pais_cliente': cuit_pais,
                'Id_impositivo': inv.partner_id.vat,
                'Moneda_Id': curr_code,
                'Moneda_ctz': curr_rate,
                'Imp_total': inv.amount_total,
                'Idioma_cbte': 1,
                'Items': items
            }

            # Datos No Obligatorios
            if inv.incoterm_id:
                Cmp['Incoterms'] = inv.incoterm_id.code
                Cmp['Incoterms_Ds'] = inv.incoterm_id.name

            if Cmps_asoc:
                Cmp['Cmps_Asoc'] = Cmps_asoc
        return Cmp
