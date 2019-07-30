##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

import logging
import re

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)

try:
    from OpenSSL import crypto
    from cryptography.hazmat.primitives import serialization
except (ImportError, IOError) as e:
    _logger.debug("Cannot import crypto from OpenSSL: \n%s" %
                  repr(e))


class WSAACertificateRequest(models.Model):
    _name = "wsaa.certificate.request"
    _description = ".csr file generation for an AFIP Certificate"

    name = fields.Char(
        string="name")
    subj_o = fields.Char(
        string="Subject Enterprise")
    subj_cn = fields.Char(
        string="Subject Hostname")
    subj_cuit = fields.Char(
        string="Subject CUIT")
    subj_c = fields.Char(
        string="Subject Country")
    partner_id = fields.Many2one(
        comodel_name='res.partner', string="Partner")
    date = fields.Date(
        string="Date", required=True,
        default=fields.Date.context_today)
    due_date = fields.Date(
        string="Due Date")
    cert_request = fields.Text(
        string="Cert Request (.csr)", readonly=True)
    old_certificate = fields.Text(
        string="Old Certificate (.crt)", readonly=True)
    certificate = fields.Text(
        string="Certificate (.crt)", readonly=True)
    key = fields.Text(
        string="Private Key (.key)", readonly=True)
    state = fields.Selection([
        ('new', _("New")),
        ('requested', _("Request Created")),
        ('done', _("Done"))], string="State",
        compute="_compute_state", store=True)

    @api.depends('certificate', 'cert_request')
    def _compute_state(self):
        for rec in self:
            if rec.certificate:
                rec.state = 'done'
                continue
            if rec.cert_request:
                rec.state = 'requested'
                continue
            rec.state = 'new'

    @api.multi
    def write(self, vals):
        if 'subj_cuit' in vals:
            normalized_cuit = self._normalize_subj_cuit(vals.get('subj_cuit'))
            vals.update({
                'subj_cuit': normalized_cuit,
            })
        if 'subj_c' in vals:
            vals.update({
                'subj_c': vals.get('subj_c').upper(),
            })
        res = super().write(vals)
        return res

    @api.model
    def _normalize_subj_cuit(self, cuit):
        pattern = '((?!\d).)*'
        cuit_number = re.sub(pattern, '', cuit)
        return 'CUIT ' + cuit_number

    @api.multi
    def generate_certificate_request(self):
        self.ensure_one()
        PrivKey = crypto.load_privatekey(crypto.FILETYPE_PEM, self.key)
        PubK_bytes = crypto.dump_publickey(crypto.FILETYPE_PEM, PrivKey)
        PubK = crypto.load_publickey(crypto.FILETYPE_PEM, PubK_bytes.decode())
        CReq = crypto.X509Req()
        CReqSubj = CReq.get_subject()
        if not all([self.subj_c, self.subj_o, self.subj_cn, self.subj_cuit]):
            try:
                Cert = crypto.load_certificate(
                    crypto.FILETYPE_PEM, self.old_certificate)
                CertSubj = Cert.get_subject()
            except Exception:
                raise ValidationError(
                    _("Either the Request Information or the " +
                      "Old Certificate must be complete!"))
        CReqSubj.C = self.subj_c or CertSubj.C
        CReqSubj.O = self.subj_o or CertSubj.O  # noqa
        CReqSubj.CN = self.subj_cn or CertSubj.CN
        CReqSubj.serialNumber = self.subj_cuit or CertSubj.serialNumber
        CReq.set_pubkey(PubK)
        CReq.sign(PrivKey, "sha256")
        CReq_bytes = crypto.dump_certificate_request(crypto.FILETYPE_PEM, CReq)
        self.cert_request = CReq_bytes.decode()

    @api.multi
    def generate_key(self):
        PKey = crypto.PKey()
        PKey.generate_key(crypto.TYPE_RSA, 2048)
        cryp_PKey = PKey.to_cryptography_key()
        serialized_key = cryp_PKey.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        self.key = serialized_key

    @api.multi
    def gather_from_cert(self):
        field = self.env.context.get('field', 'certificate')
        cert_string = getattr(self, field)
        Cert = crypto.load_certificate(
            crypto.FILETYPE_PEM, cert_string)
        CertSubj = Cert.get_subject()
        vals = {
            'subj_c': CertSubj.C,
            'subj_o': CertSubj.O,
            'subj_cn': CertSubj.CN,
            'subj_cuit': CertSubj.serialNumber,
        }
        return self.write(vals)

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
