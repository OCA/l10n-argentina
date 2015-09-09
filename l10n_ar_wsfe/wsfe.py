#' -*- coding: utf-8 -*-
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

from openerp.osv import osv
from openerp import models, fields, api
from openerp.tools.translate import _
from wsfe_suds import WSFEv1 as wsfe
from datetime import datetime
import time


class wsfe_tax_codes(models.Model):
    _name = "wsfe.tax.codes"
    _description = "Tax Codes"

    code = fields.Char('Code', required=False, size=4)
    name = fields.Char('Desc', required=True, size=64)
    to_date = fields.Date('Effect Until')
    from_date = fields.Date('Effective From')
    tax_id = fields.Many2one('account.tax', 'Account Tax')
    tax_code_id = fields.Many2one('account.tax.code', 'Account Tax Code')
    wsfe_config_id = fields.Many2one('wsfe.config', 'WSFE Configuration')
    from_afip = fields.Boolean('From AFIP')
    exempt_operations = fields.Boolean('Exempt Operations', help='Check it if this VAT Tax corresponds to vat tax exempts operations, such as to sell books, milk, etc. The taxes with this checked, will be reported to AFIP as  exempt operations (base amount) without VAT applied on this')


class wsfe_config(models.Model):
    _name = "wsfe.config"
    _description = "Configuration for WSFE"
    _rec_name = 'cuit'

    # cuit = fields.Related('company_id', 'partner_id', 'vat', type='char', string='Cuit') --> LEGACY
    cuit = fields.Char(related='company_id.partner_id.vat', string='Cuit')
    url = fields.Char('URL for WSFE', size=60, required=True)
    homologation = fields.Boolean('Homologation', help="If true, there will be some validations that are disabled, for example, invoice number correlativeness")
    point_of_sale_ids = fields.Many2many('pos.ar', 'pos_ar_wsfe_rel', 'wsfe_config_id', 'pos_ar_id', 'Points of Sale')
    vat_tax_ids = fields.One2many('wsfe.tax.codes', 'wsfe_config_id', 'Taxes', domain=[('from_afip', '=', True)])
    exempt_operations_tax_ids = fields.One2many('wsfe.tax.codes', 'wsfe_config_id', 'Taxes', domain=[('from_afip', '=', False), ('exempt_operations', '=', True)])
    wsaa_ticket_id = fields.Many2one('wsaa.ta', 'Ticket Access')
    company_id = fields.Many2one('res.company', 'Company Name', required=True)

    _sql_constraints = [
        ('company_uniq', 'unique (company_id)', 'The configuration must be unique per company !')
    ]

    _defaults = {
        'company_id': lambda self, cr, uid, context=None: self.pool.get('res.users')._get_company(cr, uid, context=context),
        'homologation': lambda *a: False,
    }

    def create(self, cr, uid, vals, context):

        # Creamos tambien un TA para este servcio y esta compania
        ta_obj = self.pool.get('wsaa.ta')
        wsaa_obj = self.pool.get('wsaa.config')
        service_obj = self.pool.get('afipws.service')

        # Buscamos primero el wsaa que corresponde a esta compania
        # porque hay que recordar que son unicos por compania
        wsaa_ids = wsaa_obj.search(cr, uid, [('company_id', '=', vals['company_id'])], context=context)
        service_ids = service_obj.search(cr, uid, [('name', '=', 'wsfe')], context=context)
        if wsaa_ids:
            ta_vals = {
                'name': service_ids[0],
                'company_id': vals['company_id'],
                'config_id': wsaa_ids[0],
            }

            ta_id = ta_obj.create(cr, uid, ta_vals, context)
            vals['wsaa_ticket_id'] = ta_id

        return super(wsfe_config, self).create(cr, uid, vals, context)

    @api.model
    def get_config(self):
        # Obtenemos la compania que esta utilizando en este momento este usuario
        company_id = self.env.user.company_id.id
        if not company_id:
            raise osv.except_osv(_('Company Error!'), _('There is no company being used by this user'))

        ids = self.search([('company_id', '=', company_id)])
        if not ids:
            raise osv.except_osv(_('WSFE Config Error!'), _('There is no WSFE configuration set to this company'))

        return ids

    @api.model
    def check_errors(self, res, raise_exception=True):
        msg = ''
        if 'errors' in res:
            errors = [error.msg for error in res['errors']]
            err_codes = [str(error.code) for error in res['errors']]
            msg = ' '.join(errors)
            msg = msg + ' Codigo/s Error:' + ' '.join(err_codes)

            if msg != '' and raise_exception:
                raise osv.except_osv(_('WSFE Error!'), msg)

        return msg

    @api.model
    def check_observations(self, res):
        msg = ''
        if 'observations' in res:
            observations = [obs.msg for obs in res['observations']]
            obs_codes = [str(obs.code) for obs in res['observations']]
            msg = ' '.join(observations)
            msg = msg + ' Codigo/s Observacion:' + ' '.join(obs_codes)

            # Escribimos en el log del cliente web
            self.log(None, msg)

        return msg

    @api.multi
    def get_invoice_CAE(self, pos, voucher_type, details):
        self.ensure_one()

        conf = self
        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfe = wsfe(conf.cuit, token, sign, conf.url)
        res = _wsfe.fe_CAE_solicitar(pos, voucher_type, details)

        return res

    @api.multi
    def _log_wsfe_request(self, pos, voucher_type_code, details, res):
        self.ensure_one()
        wsfe_req_obj = self.env['wsfe.request']
        voucher_type_obj = self.env['wsfe.voucher_type']
        voucher_type = voucher_type_obj.search([('code', '=', voucher_type_code)])
        # voucher_type_name = voucher_type_obj.read(, voucher_type_ids, ['name'])[0]['name']
        voucher_type_name = voucher_type.name
        req_details = []
        for index, comp in enumerate(res['Comprobantes']):
            detail = details[index]

            # Esto es para fixear un bug que al hacer un refund, si fallaba algo con la AFIP
            # se hace el rollback por lo tanto el refund que se estaba creando ya no existe en
            # base de datos y estariamos violando una foreign key contraint. Por eso,
            # chequeamos que existe info de la invoice_id, sino lo seteamos en False
            read_inv = self.env['account.invoice'].browse(detail['invoice_id'])

            if not read_inv:
                invoice_id = False
            else:
                invoice_id = detail['invoice_id']

            det = {
                'name': invoice_id,
                'concept': str(detail['Concepto']),
                'doctype': detail['DocTipo'],  # TODO: Poner aca el nombre del tipo de documento
                'docnum': str(detail['DocNro']),
                'voucher_number': comp['CbteHasta'],
                'voucher_date': comp['CbteFch'],
                'amount_total': detail['ImpTotal'],
                'cae': comp['CAE'],
                'cae_duedate': comp['CAEFchVto'],
                'result': comp['Resultado'],
                'observations': '\n'.join(comp['Observaciones']),
            }

            req_details.append((0, 0, det))

        # Chequeamos el reproceso
        reprocess = False
        if res['Reproceso'] == 'S':
            reprocess = True

        vals = {
            'voucher_type': voucher_type_name,
            'nregs': len(details),
            'pos_ar': '%04d' % pos,
            'date_request': time.strftime('%Y-%m-%d %H:%M:%S'),
            'result': res['Resultado'],
            'reprocess': reprocess,
            'errors': '\n'.join(res['Errores']),
            'detail_ids': req_details,
        }

        return wsfe_req_obj.create(vals)

    @api.model
    def get_last_voucher(self, pos, voucher_type):
        self.ensure_one()

        conf = self
        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfe = wsfe(conf.cuit, token, sign, conf.url)
        res = _wsfe.fe_comp_ultimo_autorizado(pos, voucher_type)

        self.check_errors(res)
        self.check_observations(res)
        last = res['response'].CbteNro
        return last

    @api.v7
    def get_voucher_info(self, cr, uid, ids, pos, voucher_type, number, context={}):
        conf = self.browse(cr, uid, ids, context=context)
        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfe = wsfe(conf.cuit, token, sign, conf.url)
        res = _wsfe.fe_comp_consultar(pos, voucher_type, number)

        # Chequeamos si hay errores
        self.check_errors(cr, uid, res)
        res = res['response']

        result = {
            'DocTipo': res[0].DocTipo,
            'DocNro': res[0].DocNro,
            'CbteDesde': res[0].CbteDesde,
            'CbteHasta': res[0].CbteHasta,
            'CbteFch': res[0].CbteFch,
            'ImpTotal': res[0].ImpTotal,
            'ImpTotConc': res[0].ImpTotConc,
            'ImpNeto': res[0].ImpNeto,
            'ImpOpEx': res[0].ImpOpEx,
            'ImpTrib': res[0].ImpTrib,
            'ImpIVA': res[0].ImpIVA,
            'FchServDesde': res[0].FchServDesde,
            'FchServHasta': res[0].FchServHasta,
            'FchVtoPago': res[0].FchVtoPago,
            'MonId': res[0].MonId,
            'MonCotiz': res[0].MonCotiz,
            'Resultado': res[0].Resultado,
            'CodAutorizacion': res[0].CodAutorizacion,
            'EmisionTipo': res[0].EmisionTipo,
            'FchVto': res[0].FchVto,
            'FchProceso': res[0].FchProceso,
            'PtoVta': res[0].PtoVta,
            'CbteTipo': res[0].CbteTipo,
        }

        return result

    @api.multi
    def read_tax(self):
        self.ensure_one()

        conf = self
        token, sign = conf.wsaa_ticket_id.get_token_sign()

        _wsfe = wsfe(conf.cuit, token, sign, conf.url)
        res = _wsfe.fe_param_get_tipos_iva()

        wsfe_tax_obj = self.env['wsfe.tax.codes']

        # Chequeamos los errores
        msg = self.check_errors(res, raise_exception=False)
        if msg:
            # TODO: Hacer un wrapping de los errores, porque algunos son
            # largos y se imprimen muy mal en pantalla
            raise osv.except_osv(_('Error reading taxes'), msg)

        #~ Armo un lista con los codigos de los Impuestos
        for r in res['response']:
            res_c = wsfe_tax_obj.search([('code', '=', r.Id)])

            #~ Si tengo no los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                fd = datetime.strptime(r.FchDesde, '%Y%m%d')
                try:
                    td = datetime.strptime(r.FchHasta, '%Y%m%d')
                except ValueError:
                    td = False

                wsfe_tax_obj.create({'code': r.Id, 'name': r.Desc, 'to_date': td,
                                              'from_date': fd, 'wsfe_config_id': self.id, 'from_afip': True})
            #~ Si los codigos estan en la db los modifico
            else:
                fd = datetime.strptime(r.FchDesde, '%Y%m%d')
                #'NULL' ?? viene asi de fe_param_get_tipos_iva():
                try:
                    td = datetime.strptime(r.FchHasta, '%Y%m%d')
                except ValueError:
                    td = False

                res_c.write({'code': r.Id, 'name': r.Desc, 'to_date': td,
                                                       'from_date': fd, 'wsfe_config_id': self.id, 'from_afip': True})

        return True

wsfe_config()
wsfe_tax_codes()


class wsfe_voucher_type(models.Model):
    """Es un comprobante que una empresa envía a su cliente, en la que se le notifica haber cargado o debitado en su cuenta una determinada suma o valor, por el concepto que se indica en la misma nota. Este documento incrementa el valor de la deuda o saldo de la cuenta, ya sea por un error en la facturación, interés por mora en el pago, o cualquier otra circunstancia que signifique el incremento del saldo de una cuenta.
It is a proof that a company sends to your client, which is notified to be charged or debited the account a certain sum or value, the concept shown in the same note. This document increases the value of the debt or account balance, either by an error in billing, interest for late payment, or any other circumstance that means the increase in the balance of an account."""
    _name = "wsfe.voucher_type"
    _description = "Voucher Type for Electronic Invoice"

    name = fields.Char('Name', size=64, required=True, readonly=False, help='Voucher Type, eg.: Factura A, Nota de Credito B, etc.')
    code = fields.Char('Code', size=4, required=True, help='Internal Code assigned by AFIP for voucher type')
    voucher_model = fields.Selection([
        ('invoice', 'Factura/NC/ND'),
        ('voucher', 'Recibo'), ], 'Voucher Model', select=True, required=True)
    document_type = fields.Selection([
        ('out_invoice', 'Factura'),
        ('out_refund', 'Nota de Credito'),
        ('out_debit', 'Nota de Debito'),
    ], 'Document Type', select=True, required=True, readonly=False)
    denomination_id = fields.Many2one('invoice.denomination', 'Denomination', required=False)

    @api.model
    def get_voucher_type(self, voucher):
        # Chequeamos el modelo
        voucher_model = None
        model = voucher._table

        if model == 'account_invoice':
            voucher_model = 'invoice'

            denomination_id = voucher.denomination_id.id
            type = voucher.type
            if type == 'out_invoice':
                # TODO: Activar esto para ND
                if voucher.is_debit_note:
                    type = 'out_debit'

            res = self.search([('voucher_model', '=', voucher_model), ('document_type', '=', type), ('denomination_id', '=', denomination_id)])

            if not len(res):
                raise osv.except_osv(_("Voucher type error!"), _("There is no voucher type that corresponds to this object"))

            if len(res) > 1:
                raise osv.except_osv(_("Voucher type error!"), _("There is more than one voucher type that corresponds to this object"))

            return res.code

        elif model == 'account_voucher':
            voucher_model = 'voucher'

        return None

wsfe_voucher_type()
