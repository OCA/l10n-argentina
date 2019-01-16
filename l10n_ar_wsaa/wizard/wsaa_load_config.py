# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2013 E-MIPS (http://www.e-mips.com.ar) All Rights Reserved.
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

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
import base64
from tempfile import TemporaryFile


class wsaa_load_config(models.TransientModel):
    _name = 'wsaa.load.config'

    @api.multi
    def read_file(self, filename=False, filedata=False,
                  ext=False, context={}):
        if not filename or not filedata or not ext:
            raise Exception('Wrong call parameters to `load_file` method')
        if not (filedata):
            raise ValidationError(_('Error ! You must enter a File'))
        pieces = filename.split('.')
        if len(pieces) < 2 or pieces[-1] != ext:
            raise ValidationError(
                _('Error ! The Filename should end in ".%s"', ext))
        fileobj = TemporaryFile('w+')
        fileobj.write(base64.b64decode(filedata).decode('utf-8'))
        fileobj.seek(0)
        lines = fileobj.read()
        fileobj.close()
        return lines

    @api.multi
    def load_cert(self):
        form_id = self.env.context.get('active_ids', False)
        if not form_id or len(form_id) != 1:
            raise Exception('Wizard method call without `active_ids` in ctx')
        wiz = self
        certificate = wiz.certificate
        cert_name = wiz.cert_name
        filedata = self.read_file(cert_name, certificate, 'crt')
        wsaa_config_model = self.env['wsaa.config']
        wsaa_config = wsaa_config_model.browse(form_id)
        write_vals = {
            'certificate': filedata,
        }
        wsaa_config.write(write_vals)

    @api.multi
    def load_key(self):
        form_id = self.env.context.get('active_ids', False)
        if not form_id or len(form_id) != 1:
            raise Exception('Wizard method call without `active_ids` in ctx')
        wiz = self
        key = wiz.key
        key_name = wiz.key_name
        filedata = self.read_file(key_name, key, 'key')
        wsaa_config_model = self.env['wsaa.config']
        wsaa_config = wsaa_config_model.browse(form_id)
        write_vals = {
            'key': filedata,
        }
        wsaa_config.write(write_vals)

    certificate = fields.Binary('Certificate of Approval',
                                help="You certificate (.crt)",
                                filter="*.crt")
    cert_name = fields.Char('Cert FileName')
    key = fields.Binary('Private Key',
                        help="You Privary Key Here",
                        filter="*.key")
    key_name = fields.Char('Key FileName')
