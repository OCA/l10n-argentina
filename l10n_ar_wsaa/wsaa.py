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

from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, timedelta
from wsaa_suds import WSAA as wsaa
from openerp import SUPERUSER_ID
import pytz

class wsaa_config(osv.osv):
    _name = "wsaa.config"
    _description = "Configuration for WSAA"

    _columns = {
        'name': fields.char('Description', size=255),
        'certificate': fields.text ('Certificate', readonly=True),
        'key': fields.text ('Private Key' , readonly=True),
        'url' : fields.char('URL for WSAA', size=60, required=True),
        'company_id' : fields.many2one('res.company', 'Company Name' , required=True),
        'service_ids' : fields.one2many('wsaa.ta', 'config_id', string="Authorized Services"),
    }

    _sql_constraints = [
        ('company_uniq', 'unique (company_id)', 'The configuration must be unique per company !')
    ]

    _defaults = {
        'company_id' : lambda self, cr, uid, context=None: self.pool.get('res.users')._get_company(cr, uid, context=context),
        }

wsaa_config()

class afipws_service(osv.osv):
    _name = "afipws.service"
    _description = "WS Services"

    _columns = {
        'name': fields.char('Service Name', size=16, required=True),
        'description': fields.text('Description'),
        }

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the service must be unique!')
    ]

afipws_service()

class wsaa_ta(osv.osv):
    _name = "wsaa.ta"
    _description = "Ticket Access for WSAA"

    _columns = {
        'name': fields.many2one('afipws.service', 'Service'),
        'token': fields.text('Token', readonly=True),
        'sign': fields.text('Sign', readonly=True),
        'expiration_time': fields.char('Expiration Time', size=256),
        'config_id' : fields.many2one('wsaa.config'),
        'company_id' : fields.many2one('res.company', 'Company Name'),
    }

    _sql_constraints = [
        ('company_name_uniq', 'unique (name, company_id)', 'The service must be unique per company!')
    ]

    def _renew_ticket(self, cr, uid, wsaa_config, service, context=None):

        user_obj = self.pool.get('res.users')
        user = user_obj.browse(cr, SUPERUSER_ID, uid)
        tz = pytz.timezone(user.partner_id.tz) or pytz.utc
        try:
            _wsaa = wsaa(wsaa_config.certificate, wsaa_config.key, wsaa_config.url, service, tz)
            _wsaa.get_token_and_sign(wsaa_config.certificate, wsaa_config.key)
        except Exception, e:
            raise osv.except_osv(_('WSAA Error!'), e)

        vals = {
            'token': _wsaa.token,
            'sign': _wsaa.sign,
            'expiration_time' : _wsaa.expiration_time.strftime('%Y-%m-%d %H:%M:%S'),
            }

        return vals

    def get_token_sign(self, cr, uid, ids, context=None):

        ticket = self.browse(cr, uid, ids, context=context)[0]
        force = context.get('force_renew', False)

        if not force:
            if ticket.expiration_time:
                expiration_time = datetime.strptime(ticket.expiration_time, '%Y-%m-%d %H:%M:%S')
                # Primero chequemos si tenemos ya un ticket expirado
                # Si ahora+10 minutos es mayor al momento de expiracion
                # debemos renovar el ticket.
                if datetime.now()+timedelta(minutes=10) < expiration_time:
                    return ticket.token, ticket.sign

        service = ticket.name.name
        vals = self._renew_ticket(cr, uid, ticket.config_id, service, context=context)
        self.write(cr, uid, ticket.id, vals, context=context)
        return vals['token'], vals['sign']

    def action_renew(self, cr, uid, ids, context=None):
        if not context:
            context = {}

        context['force_renew'] = True
        self.get_token_sign(cr, uid, ids, context=context)
        return True



wsaa_ta()
