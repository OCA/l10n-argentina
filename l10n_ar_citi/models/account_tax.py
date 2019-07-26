##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import models, fields, api


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'
    OPERATION_CODES = [
        ('Z', 'Exports to free zone'),
        ('X', 'Overseas Exports'),
        ('E', 'Exempt Operation'),
        ('N', 'No Taxed Operation'),
        (' ', 'Internal'),
    ]

    afip_code = fields.Char('AFIP Code', size=3)
    operation_code = fields.Selection(selection=OPERATION_CODES)


class AccountTax(models.Model):
    _inherit = 'account.tax'

    afip_code = fields.Char(
        'AFIP Code', size=3,
        help="Code specified by AFIP to use in CITI reports. " +
        "Should not be changed")

    @api.model
    def _set_default_afip_codes(self):
        taxes = self.search([('tax_group', '=', 'vat')])
        for tax in taxes:
            if tax.afip_code:
                continue
            if 'no gravado' in tax.name.lower():
                tax.write({"afip_code": "1"})
            elif 'exento' in tax.name.lower():
                tax.write({"afip_code": "3"})
            elif '10.5' in tax.name:
                tax.write({"afip_code": "4"})
            elif '21' in tax.name:
                tax.write({"afip_code": "5"})
            elif '27' in tax.name:
                tax.write({"afip_code": "6"})
            elif 'gravado' in tax.name.lower():
                tax.write({"afip_code": "7"})
            elif '5' in tax.name:
                tax.write({"afip_code": "8"})
            elif '2.5' in tax.name:
                tax.write({"afip_code": "9"})
            elif '0' in tax.name:
                tax.write({"afip_code": "3"})
            else:
                tax.write({"afip_code": "0"})
