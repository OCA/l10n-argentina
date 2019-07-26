##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import models, fields, api


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    afip_code = fields.Char('AFIP Code', size=3)

    @api.model
    def rcref(self, mon_str):
        return self.env.ref('base.%s' % mon_str)

    @api.model
    def _set_default_afip_codes(self):
        currencies = self.search([])
        ars = self.rcref('ARS')
        dol = self.rcref('USD')
        euro = self.rcref('EUR')
        real = self.rcref('BRL')
        yen = self.rcref('JPY')
        uru = self.rcref('UYU')
        chi = self.rcref('CLP')
        col = self.rcref('COP')
        libra = self.rcref('LBP')
        can = self.rcref('CAD')
        yuan = self.rcref('CNY')
        for currency in currencies:
            if currency.afip_code:
                continue
            if currency == ars:
                currency.write({'afip_code': 'PES'})
            elif currency == dol:
                currency.write({'afip_code': 'DOL'})
            elif currency == euro:
                currency.write({'afip_code': '060'})
            elif currency == real:
                currency.write({'afip_code': '012'})
            elif currency == yen:
                currency.write({'afip_code': '019'})
            elif currency == uru:
                currency.write({'afip_code': '011'})
            elif currency == chi:
                currency.write({'afip_code': '033'})
            elif currency == col:
                currency.write({'afip_code': '032'})
            elif currency == libra:
                currency.write({'afip_code': '021'})
            elif currency == can:
                currency.write({'afip_code': '018'})
            elif currency == yuan:
                currency.write({'afip_code': '064'})
            else:
                currency.write({'afip_code': '0'})
