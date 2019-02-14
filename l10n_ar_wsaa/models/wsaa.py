###############################################################################
#    Copyright (c) 2013-2014 Eynes/E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from odoo import models, fields, api
# sfrom openerp.osv import osv
from datetime import datetime, timedelta
from odoo.addons.l10n_ar_wsaa.utils.wsaa_suds import WSAA as wsaa
from odoo import SUPERUSER_ID
import pytz


class wsaa_config(models.Model):
    _name = "wsaa.config"
    _description = "Configuration for WSAA"

    name = fields.Char('Description', size=255)
    certificate = fields.Text('Certificate', readonly=True)
    key = fields.Text('Private Key', readonly=True)
    url = fields.Char('URL for WSAA', size=60, required=True)
    company_id = fields.Many2one(
        'res.company', 'Company Name', required=True,
        default=lambda self: self.env.user.company_id.id)
    service_ids = fields.One2many('wsaa.ta', 'config_id',
                                  string="Authorized Services")

    _sql_constraints = [
        ('company_uniq',
         'unique (company_id)',
         'The configuration must be unique per company !')
    ]

    @api.multi
    def download_file(self):
        self.ensure_one()
        field = self.env.context.get('field')
        fname = self.env.context.get('filename')
        vals = {
            'model': self._name,
            'field': field,
            'id': self.id,
            'fname': fname,
        }
        action = {
            'type': 'ir.actions.act_url',
            'url': ('/web/binary/download_document?model=%(model)s&' +
                    'field=%(field)s&id=%(id)s&filename=%(fname)s') % vals,
            'target': 'new',
        }
        return action


class afipws_service(models.Model):
    _name = "afipws.service"
    _description = "WS Services"

    name = fields.Char('Service Name', size=16, required=True)
    description = fields.Text('Description')

    _sql_constraints = [
        ('name_uniq',
         'unique (name)',
         'The name of the service must be unique!')
    ]


class wsaa_ta(models.Model):
    _name = "wsaa.ta"
    _description = "Ticket Access for WSAA"

    name = fields.Many2one('afipws.service', 'Service')
    token = fields.Text('Token', readonly=True)
    sign = fields.Text('Sign', readonly=True)
    expiration_time = fields.Char('Expiration Time', size=256)
    config_id = fields.Many2one('wsaa.config')
    company_id = fields.Many2one('res.company', 'Company Name')

    _sql_constraints = [
        ('company_name_uniq',
         'unique (name, company_id)',
         'The service must be unique per company!')
    ]

    @api.model
    def _renew_ticket(self):

        wsaa_config = self.config_id
        service = self.name.name
        user = self.env['res.users'].browse(SUPERUSER_ID)
        # user = user_obj.browse(cr, SUPERUSER_ID, uid)
        tz = pytz.timezone(user.partner_id.tz) or pytz.utc
        _wsaa = wsaa(wsaa_config.certificate, wsaa_config.key,
                     wsaa_config.url, service, tz)
        _wsaa.get_token_and_sign(wsaa_config.certificate, wsaa_config.key)

        vals = {
            'token': _wsaa.token,
            'sign': _wsaa.sign,
            'expiration_time': _wsaa.expiration_time.strftime(
                '%Y-%m-%d %H:%M:%S'),
        }
        return vals

    @api.multi
    def get_token_sign(self):
        ticket = self
        force = self._context.get('force_renew', False)

        if not force:
            if ticket.expiration_time:
                expiration_time = datetime.strptime(ticket.expiration_time,
                                                    '%Y-%m-%d %H:%M:%S')
                # Primero chequemos si tenemos ya un ticket expirado
                # Si ahora+10 minutos es mayor al momento de expiracion
                # debemos renovar el ticket.
                print(datetime.now() + timedelta(minutes=10))
                if datetime.now() + timedelta(minutes=10) < expiration_time:
                    return ticket.token, ticket.sign

        # service = ticket.name.name
        # vals = self._renew_ticket(ticket.config_id, service)

        vals = self._renew_ticket()
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            new_env = api.Environment(new_cr, self.env.user.id,
                                      self.env.context)
            new_env['wsaa.ta'].browse(self.id).write(vals)
            new_cr.commit()
            new_cr.close()
        return vals['token'], vals['sign']

    @api.multi
    def action_renew(self):
        self.with_context(force_renew=True).get_token_sign()
        return True
