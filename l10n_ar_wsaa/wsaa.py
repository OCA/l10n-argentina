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

from osv import osv, fields

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
        'token': fields.char('Token', size=256),
        'sign': fields.char('Sign', size=256),
        'expiration_time': fields.char('Expiration Time', size=256),
        'config_id' : fields.many2one('wsaa.config'),
        'company_id' : fields.many2one('res.company', 'Company Name'),
    }

    _sql_constraints = [
        ('company_name_uniq', 'unique (name, company_id)', 'The service must be unique per company!')
    ]

wsaa_ta()
