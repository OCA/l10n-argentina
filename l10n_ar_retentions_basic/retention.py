# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2011
# 
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from osv import osv, fields
import decimal_precision as dp

class retention_retention(osv.osv):
    """Objeto que define las retenciones que pueden utilizarse

       Configura las retenciones posibles. Luego a partir de estos objetos
       se crean las retention.tax que serian retenciones aplicadas a un recibo;
       las retention.tax toman la configuracion de la retention.retention que la
       genera y se le agrega la informacion del impuesto en si, como por ejemplo,
       monto, base imponible, nro de certificado, etc."""
    _name = "retention.retention"
    _description = "Retention Configuration"

    #TODO: Tal vez haya que agregar algun campo mas para saber si 
    # se aplica a ventas o compras, asi podemos filtrar por domain
    _columns = {
            'name': fields.char('Retention', required=True, size=64),
            'tax_id': fields.many2one('account.tax', 'Tax', required=True, help="Tax configuration for this retention"),
            }

retention_retention()

class retention_tax(osv.osv):
    _name = "retention.tax"
    _description = "Retention Tax"

    #TODO: Tal vaz haya que ponerle estados a este objeto para manejar tambien propiedades segun estados
    _columns = {
        'name': fields.char('Retention', required=True, size=64),
        'voucher_id': fields.many2one('account.voucher', 'Voucher'),
        'account_id': fields.many2one('account.account', 'Tax Account', required=True, 
                                      domain=[('type','<>','view'),('type','<>','income'), ('type', '<>', 'closed')]),

        'base': fields.float('Base', digits_compute=dp.get_precision('Account')),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account')),
        'retention_id': fields.many2one('retention.retention', 'Retention Configuration', help="Retention configuration used '\
                                       'for this retention tax, where all the configuration resides. Accounts, Tax Codes, etc."),
        'base_code_id': fields.many2one('account.tax.code', 'Base Code', help="The account basis of the tax declaration."),
        'base_amount': fields.float('Base Code Amount', digits_compute=dp.get_precision('Account')),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Code', help="The tax basis of the tax declaration."),
        'tax_amount': fields.float('Tax Code Amount', digits_compute=dp.get_precision('Account')),
        'company_id': fields.related('account_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        #'factor_base': fields.function(_count_factor, method=True, string='Multipication factor for Base code', type='float', multi="all"),
        #'factor_tax': fields.function(_count_factor, method=True, string='Multipication factor Tax code', type='float', multi="all")
    }

retention_tax()
