##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.l10n_ar_wsfe.wsfetools.wsfex_easywsy import WSFEX


class StockIncoterms(models.Model):
    _name = 'stock.incoterms'
    _inherit = 'stock.incoterms'

    @api.multi
    def name_get(self):
        res = []
        for inc in self:
            name_lst = []
            if inc.code:
                name_lst.append("[%s]" % inc.code)
            name_lst.append(inc.name)
            name = (" ").join(name_lst)
            res.append((inc.id, name))
        return res


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

    _webservice_class = WSFEX

    name = fields.Char('Name', size=64, required=True)
    cuit = fields.Char(related='company_id.partner_id.vat', string='Cuit')
    url = fields.Char('URL for WSFEX', size=60, required=True)
    homologation = fields.Boolean(
        comodel_name='Homologation',
        default=False,
        help="If true, there will be some validations that are \
        disabled, for example, invoice number correlativeness")
    point_of_sale_ids = fields.Many2many(
        comodel_name='pos.ar', relation='pos_ar_wsfex_rel',
        column1='wsfex_config_id', column2='pos_ar_id',
        string='Points of Sale')
    wsaa_ticket_id = fields.Many2one(
        comodel_name='wsaa.ta', string='Ticket Access')
    currency_ids = fields.One2many(
        comodel_name='wsfex.currency.codes',
        inverse_name='wsfex_config_id', string='Currencies')
    uom_ids = fields.One2many(
        comodel_name='wsfex.uom.codes',
        inverse_name='wsfex_config_id', string='Units of Measure')
    lang_ids = fields.One2many(
        comodel_name='wsfex.lang.codes',
        inverse_name='wsfex_config_id', string='Languages')
    country_ids = fields.One2many(
        comodel_name='wsfex.dst_country.codes',
        inverse_name='wsfex_config_id', string='Countries')
    incoterms_ids = fields.One2many(
        comodel_name='wsfex.incoterms.codes',
        inverse_name='wsfex_config_id', string='Incoterms')
    dst_cuit_ids = fields.One2many(
        comodel_name='dst_cuit.codes',
        inverse_name='wsfex_config_id', string='DST CUIT')
    voucher_type_ids = fields.One2many(
        comodel_name='wsfex.voucher_type.codes',
        inverse_name='wsfex_config_id', string='Voucher Type')
    export_type_ids = fields.One2many(
        comodel_name='wsfex.export_type.codes',
        inverse_name='wsfex_config_id', string='Export Type')
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company Name',
        default=lambda self: self.env['res.users']._get_company(),
        required=True)

    @property
    def voucher_type_str(self):
        if self.homologation:
            vt_str = 'Cbte_Tipo'
        else:
            vt_str = 'Tipo_Cbte'
        return vt_str

    @api.multi
    def ws_auth(self):
        # TODO This block is repeated, should persist only in WSAA, I think
        token, sign = self.wsaa_ticket_id.get_token_sign()
        auth = {
            'Token': token,
            'Sign': sign,
            'Cuit': self.cuit
        }
        ws = self._webservice_class(self.url)
        ws.login('Auth', auth)
        return ws

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
        company_id = self.env.context.get('company_id')
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

    @api.multi
    def fexgetparam_method(self, method_ext):
        self.ensure_one()
        method_name = 'FEXGetPARAM_%s' % method_ext
        ws = self.ws_auth()

        data = {
            method_name: {
            },
        }
        ws.add(data)
        response = ws.request(method_name)
        res = ws.parse_response(response)
        del(ws)
        return res['response'].FEXResultGet[0]

    @api.one
    def get_wsfex_currencies(self):
        self.ensure_one()
        res = self.fexgetparam_method('MON')

        wsfex_cur_obj = self.env['wsfex.currency.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res:
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
        self.ensure_one()
        res = self.fexgetparam_method('UMed')

        wsfex_uom_obj = self.env['wsfex.uom.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res:
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
        self.ensure_one()
        res = self.fexgetparam_method('Idiomas')

        wsfex_param_obj = self.env['wsfex.lang.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res:
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
        res = self.fexgetparam_method('Tipo_Expo')

        wsfex_param_obj = self.env['wsfex.export_type.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res:
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
        res = self.fexgetparam_method('DST_pais')

        wsfex_param_obj = self.env['wsfex.dst_country.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res:
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
        self.ensure_one()
        res = self.fexgetparam_method('Incoterms')

        wsfex_param_obj = self.env['wsfex.incoterms.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res:
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
        res = self.fexgetparam_method('DST_CUIT')

        param_obj = self.env['dst_cuit.codes']

        # Armo un lista con los codigos de los Impuestos
        for r in res:
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
        res = self.fexgetparam_method(self.voucher_type_str)

        wsfex_param_obj = self.env['wsfex.voucher_type.codes']
        # Armo un lista con los codigos de los Impuestos
        for r in res:
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

    @api.multi
    def get_last_voucher(self, pos, voucher_type):
        self.ensure_one()
        ws = self.ws_auth()
        data = {
            'FEXGetLast_CMP': {
                'CbteTipo': voucher_type,
                'PtoVta': pos,
            }
        }
        ws.add(data)
        response = ws.request('FEXGetLast_CMP')
        res = ws.parse_response(response)
        del(ws)
        last = res['response'].Cbte_nro
        return last
