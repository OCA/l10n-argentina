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

from osv import osv, fields
from tools.translate import _
from wsfe_suds import WSFEv1 as wsfe
from datetime import datetime


class wsfe_tax_codes(osv.osv):
    _name = "wsfe.tax.codes"
    _description = "Tax Codes"
    _columns = {
        'code' : fields.char('Code', required=False, size=4),
        'name' : fields.char('Desc', required=True, size=64),
        'to_date' : fields.date('Effect Until'),
        'from_date' : fields.date('Effective From'),
        'tax_id' : fields.many2one('account.tax','Account Tax'),
        'tax_code_id': fields.many2one('account.tax.code', 'Account Tax Code'),
        'wsfe_config_id' : fields.many2one('wsfe.config','WSFE Configuration'),
        'from_afip': fields.boolean('From AFIP'),
        'exempt_operations': fields.boolean('Exempt Operations', help='Check it if this VAT Tax corresponds to vat tax exempts operations, such as to sell books, milk, etc. The taxes with this checked, will be reported to AFIP as  exempt operations (base amount) without VAT applied on this'),
    }


class wsfe_config(osv.osv):
    _name = "wsfe.config"
    _description = "Configuration for WSFE"
    _rec_name = 'cuit'

    _columns = {
        'cuit': fields.related('company_id', 'partner_id', 'vat', type='char', string='Cuit'),
        'url' : fields.char('URL for WSFE', size=60, required=True),
        'point_of_sale_ids': fields.many2many('pos.ar', 'pos_ar_wsfe_rel', 'wsfe_config_id', 'pos_ar_id', 'Points of Sale'),
        'vat_tax_ids' : fields.one2many('wsfe.tax.codes', 'wsfe_config_id' ,'Taxes', domain=[('from_afip', '=', True)]),
        'exempt_operations_tax_ids' : fields.one2many('wsfe.tax.codes', 'wsfe_config_id' ,'Taxes', domain=[('from_afip', '=', False), ('exempt_operations', '=', True)]),
        'wsaa_ticket_id' : fields.many2one('wsaa.ta', 'Ticket Access'),
        'company_id' : fields.many2one('res.company', 'Company Name' , required=True),
    }

    _sql_constraints = [
        ('company_uniq', 'unique (company_id)', 'The configuration must be unique per company !')
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
        service_ids = service_obj.search(cr, uid, [('name','=', 'wsfe')], context=context)
        if wsaa_ids:
            ta_vals = {
                'name': service_ids[0],
                'company_id': vals['company_id'],
                'config_id' : wsaa_ids[0],
                }

            ta_id = ta_obj.create(cr, uid, ta_vals, context)
            vals['wsaa_ticket_id'] = ta_id

        return super(wsfe_config, self).create(cr, uid, vals, context)

    def check_errors(self, res):
        msg = ''
        if 'errors' in res:
            errors = [error.msg for error in res['errors']]
            err_codes = [str(error.code) for error in res['errors']]
            msg = ' '.join(errors)
            msg = msg + ' Codigo/s Error:' + ' '.join(err_codes)
            return msg

    def check_observations(self, res):
        msg = ''
        if 'observations' in res:
            observations = [obs.msg for obs in res['observations']]
            obs_codes = [str(obs.code) for obs in res['observations']]
            msg = ' '.join(observations)
            msg = msg + ' Codigo/s Observacion:' + ' '.join(obs_codes)

            # Escribimos en el log del cliente web
            #self.log(cr, uid, inv_id, msg, context)
            return msg



    def read_tax(self, cr, uid , ids , context={}):
        ta_obj = self.pool.get('wsaa.ta')

        conf = self.browse(cr, uid, ids)[0]
        token, sign = ta_obj.get_token_sign(cr, uid, [conf.wsaa_ticket_id.id], context=context)

        _wsfe = wsfe(conf.cuit, token, sign, conf.url)
        res = _wsfe.fe_param_get_tipos_iva()

        wsfe_tax_obj = self.pool.get('wsfe.tax.codes')

        # Chequeamos los errores
        msg = self.check_errors(res)
        if msg:
            # TODO: Hacer un wrapping de los errores, porque algunos son
            # largos y se imprimen muy mal en pantalla
            raise osv.except_osv(_('Error reading taxes'), msg)

        #~ Armo un lista con los codigos de los Impuestos
        for r in res['response']:
            res_c = wsfe_tax_obj.search(cr, uid , [('code','=', r.Id )])

            #~ Si tengo no los codigos de esos Impuestos en la db, los creo
            if not len(res_c):
                fd = datetime.strptime(r.FchDesde, '%Y%m%d')
                try:
                    td = datetime.strptime(r.FchHasta, '%Y%m%d')
                except ValueError:
                    td = False

                wsfe_tax_obj.create(cr, uid , {'code': r.Id, 'name': r.Desc, 'to_date': td,
                        'from_date': fd, 'wsfe_config_id': ids[0], 'from_afip': True } , context={})
            #~ Si los codigos estan en la db los modifico
            else :
                fd = datetime.strptime(r.FchDesde, '%Y%m%d')
                #'NULL' ?? viene asi de fe_param_get_tipos_iva():
                try:
                    td = datetime.strptime(r.FchHasta, '%Y%m%d')
                except ValueError:
                    td = False

                wsfe_tax_obj.write(cr, uid , res_c[0] , {'code': r.Id, 'name': r.Desc, 'to_date': td ,
                    'from_date': fd, 'wsfe_config_id': ids[0], 'from_afip': True } )

        return True

wsfe_config()
wsfe_tax_codes()
