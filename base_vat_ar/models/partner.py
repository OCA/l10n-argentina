###############################################################################
#   Copyright (c) 2017-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

__author__ = "Sebastian Kennedy <skennedy@e-mips.com.ar>,"\
             "Anibal Alejandro Guanca <aguanca@e-mips.com.ar>"


class ResDocumentType(models.Model):
    _name = "res.document.type"
    _description = 'Document type'

    name = fields.Char(string='Document type', size=40)
    afip_code = fields.Char(string='Afip code', size=10)
    verification_required = fields.Boolean(string='Verification required',
                                           default=lambda *a: False)

    def get_website_sale_documents(self, mode='billing'):
        cuit = self.sudo().env.ref(
            'base_vat_ar.document_cuit').name
        cuil = self.sudo().env.ref(
            'base_vat_ar.document_cuil').name
        dni = self.sudo().env.ref(
            'base_vat_ar.document_dni').name
        return self.sudo().search([(
            'name', 'in', (cuit, cuil, dni))])


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    document_type_id = fields.Many2one('res.document.type',
                                       string='Document type')

    @api.constrains('vat', 'document_type_id')
    def check_vat_duplicated(self):
        for partner in self:
            if partner.env.context.get('from_website', False):
                continue
            if not partner.vat:
                continue
            search_param = [
                ('vat', '=', partner.vat),
                ('document_type_id', '=', partner.document_type_id.id),
                ('parent_id', '=', False)
            ]
            res = self.search_count(search_param)
            if res > 1:
                raise ValidationError(
                    _('There is another partner with same VAT Information'))

    @api.multi
    def write(self, vals):
        self.check_vat_string(vals)
        res = super().write(vals)
        return res

    @api.multi
    def check_vat_string(self, vals):
        vat = vals.get("vat")
        if not vat:
            return False
        ci_extranjera = self.env.ref(
            'base_vat_ar.document_ci_extranjera')
        pasaporte = self.env.ref(
            'base_vat_ar.document_pasaporte')
        if [x for x in self if x.document_type_id not in [ci_extranjera,
                                                          pasaporte]]:
            vat = vat.replace('.', '').replace('-', '')
            if not vat.isdigit():
                raise ValidationError(
                    _('The Vat only supports numbers.'))
            vals['vat'] = vat
        return False

    @api.constrains('vat', 'country_id', 'document_type_id')
    def check_vat(self):
        '''
        Check the VAT number depending of the country.
        '''
        for partner in self:
            if not partner.vat:
                continue
            if partner.country_id:
                vat_country = partner.country_id.code.lower()
                vat_number = partner.vat
            else:
                vat_country, vat_number = partner.vat[:2].lower(), \
                    partner.vat[2:].replace(' ', '')
            if partner.document_type_id and \
                    not partner.document_type_id.sudo().verification_required:
                return True
            if not hasattr(self, 'check_vat_' + vat_country):
                return True
            check = getattr(self, 'check_vat_' + vat_country)
            if not check(vat_number):
                raise ValidationError(
                    _('The Vat does not seems to be correct.'))
        return True

    @api.model
    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + \
            ['document_type_id']

    def check_vat_ar(self, vat):
        """
        Check VAT Routine for Argentina.
        """
        if len(vat) != 11:
            return False
        try:
            int(vat)
        except ValueError:
            return False

        l = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]

        var1 = 0
        for i in range(10):
            var1 = var1 + int(vat[i]) * l[i]
        var3 = 11 - var1 % 11

        if var3 == 11:
            var3 = 0
        if var3 == 10:
            var3 = 9
        if var3 == int(vat[10]):

            return True

        return False
