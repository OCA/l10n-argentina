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
import base64
from tempfile import TemporaryFile

class wsaa_load_config(osv.osv_memory):
    _name = 'wsaa.load.config'
    _inherit = 'res.config'
    _columns = {
        'certificate': fields.binary('Certificate of Approval', help="You certificate (.crt)", filter="*.crt" , required=True),
        'key': fields.binary('Private Key',help="You Privary Key Here" ,filter="*.key" , required=True),
        'wsaa' : fields.char('URL for WSAA', size=60, required=True),
        'company_id' : fields.many2one('res.company', 'Company Name' , required=True),
    }

    def read_cert(self, cr, uid, certificate, context):
        if not (certificate):
            raise osv.except_osv( ('Error') , ('You must enter your Certification file'))
        fileobj = TemporaryFile('w+')
        fileobj.write(base64.decodestring(certificate))
        fileobj.seek(0)
        lines = fileobj.read()
        fileobj.close()
        return lines

    def read_key (self, cr, uid, key, context):
        if not (key):
            raise osv.except_osv( ('Error') , ('You must enter your Private Key file '))
        fileobj = TemporaryFile('w+')
        fileobj.write(base64.decodestring(key))
        fileobj.seek(0)
        lines = fileobj.read()
        fileobj.close()
        return lines

    def execute(self, cr, uid, ids, context=None):
        data = self.browse(cr, uid, ids, context=context)[0]
        wsaa_url = data.wsaa
        if not ( wsaa_url.endswith('?wsdl') ):
            wsaa_url+='?wsdl'

        wsaa_config_obj = self.pool.get('wsaa.config')
        cer     = self.read_cert(cr, uid, data.certificate, context=context)
        key       = self.read_key(cr, uid, data.key, context=context)
        comp    = data.company_id
        res     = wsaa_config_obj.search(cr, uid , [('company_id','=', comp.id)])

        if not len(res):
            wsaa_config_obj.create(cr, uid , {'certificate': cer, 'key': key, 'url': wsaa_url, 'company_id': comp.id  }
            , context={})
        else :
            wsaa_config_obj.write(cr, uid , res[0],  {'certificate': cer, 'key': key, 'url': wsaa_url, 'company_id': comp.id  } )

wsaa_load_config()
