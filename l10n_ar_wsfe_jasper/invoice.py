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

from openerp import models, fields, api
from datetime import datetime
from itertools import ifilter

__author__ = "Sebastian Kennedy <skennedy@e-mips.com.ar>"

UNIDADES = (
    '',
    'UN ',
    'DOS ',
    'TRES ',
    'CUATRO ',
    'CINCO ',
    'SEIS ',
    'SIETE ',
    'OCHO ',
    'NUEVE ',
    'DIEZ ',
    'ONCE ',
    'DOCE ',
    'TRECE ',
    'CATORCE ',
    'QUINCE ',
    'DIECISEIS ',
    'DIECISIETE ',
    'DIECIOCHO ',
    'DIECINUEVE ',
    'VEINTE '
)

DECENAS = (
    'VENTI',
    'TREINTA ',
    'CUARENTA ',
    'CINCUENTA ',
    'SESENTA ',
    'SETENTA ',
    'OCHENTA ',
    'NOVENTA ',
    'CIEN '
)

CENTENAS = (
    'CIENTO ',
    'DOSCIENTOS ',
    'TRESCIENTOS ',
    'CUATROCIENTOS ',
    'QUINIENTOS ',
    'SEISCIENTOS ',
    'SETECIENTOS ',
    'OCHOCIENTOS ',
    'NOVECIENTOS '
)

UNITS = (
        ('', ''),
        ('MIL ', 'MIL '),
        ('MILLON ', 'MILLONES '),
        ('MIL MILLONES ', 'MIL MILLONES '),
        ('BILLON ', 'BILLONES '),
        ('MIL BILLONES ', 'MIL BILLONES '),
        ('TRILLON ', 'TRILLONES '),
        ('MIL TRILLONES', 'MIL TRILLONES'),
        ('CUATRILLON', 'CUATRILLONES'),
        ('MIL CUATRILLONES', 'MIL CUATRILLONES'),
        ('QUINTILLON', 'QUINTILLONES'),
        ('MIL QUINTILLONES', 'MIL QUINTILLONES'),
        ('SEXTILLON', 'SEXTILLONES'),
        ('MIL SEXTILLONES', 'MIL SEXTILLONES'),
        ('SEPTILLON', 'SEPTILLONES'),
        ('MIL SEPTILLONES', 'MIL SEPTILLONES'),
        ('OCTILLON', 'OCTILLONES'),
        ('MIL OCTILLONES', 'MIL OCTILLONES'),
        ('NONILLON', 'NONILLONES'),
        ('MIL NONILLONES', 'MIL NONILLONES'),
        ('DECILLON', 'DECILLONES'),
        ('MIL DECILLONES', 'MIL DECILLONES'),
        ('UNDECILLON', 'UNDECILLONES'),
        ('MIL UNDECILLONES', 'MIL UNDECILLONES'),
        ('DUODECILLON', 'DUODECILLONES'),
        ('MIL DUODECILLONES', 'MIL DUODECILLONES'),
)


MONEDAS = (
    {'country': u'Colombia', 'currency': 'COP', 'singular': u'PESO COLOMBIANO', 'plural': u'PESOS COLOMBIANOS', 'symbol': u'$'},
    {'country': u'Estados Unidos', 'currency': 'USD', 'singular': u'DÓLAR', 'plural': u'DÓLARES', 'symbol': u'US$'},
    {'country': u'Europa', 'currency': 'EUR', 'singular': u'EURO', 'plural': u'EUROS', 'symbol': u'€'},
    {'country': u'México', 'currency': 'MXN', 'singular': u'PESO MEXICANO', 'plural': u'PESOS MEXICANOS', 'symbol': u'$'},
    {'country': u'Perú', 'currency': 'PEN', 'singular': u'NUEVO SOL', 'plural': u'NUEVOS SOLES', 'symbol': u'S/.'},
    {'country': u'Reino Unido', 'currency': 'GBP', 'singular': u'LIBRA', 'plural': u'LIBRAS', 'symbol': u'£'}
)
# Para definir la moneda me estoy basando en los código que establece el ISO 4217
# Decidí poner las variables en inglés, porque es más sencillo de ubicarlas sin importar el país
# Si, ya sé que Europa no es un país, pero no se me ocurrió un nombre mejor para la clave.


def hundreds_word(number):
    """Converts a positive number less than a thousand (1000) to words in Spanish

    Args:
        number (int): A positive number less than 1000
    Returns:
        A string in Spanish with first letters capitalized representing the number in letters

    Examples:
        >>> to_word(123)
        'Ciento Ventitres'
    """
    converted = ''
    if not (0 < number < 1000):
        return 'No es posible convertir el numero a letras'

    number_str = str(number).zfill(9)
    cientos = number_str[6:]

    if(cientos):
        if(cientos == '001'):
            converted += 'UN '
        elif(int(cientos) > 0):
            converted += '%s ' % __convert_group(cientos)

    return converted.title().strip()


def __convert_group(n):
    """Turn each group of numbers into letters"""
    output = ''

    if(n == '100'):
        output = "CIEN "
    elif(n[0] != '0'):
        output = CENTENAS[int(n[0]) - 1]

    k = int(n[1:])
    if(k <= 20):
        output += UNIDADES[k]
    else:
        if((k > 30) & (n[2] != '0')):
            output += '%sY %s' % (DECENAS[int(n[1]) - 2], UNIDADES[int(n[2])])
        else:
            output += '%s%s' % (DECENAS[int(n[1]) - 2], UNIDADES[int(n[2])])

    return output


def to_word(number, mi_moneda=None):

    """Converts a positive number less than:
    (999999999999999999999999999999999999999999999999999999999999999999999999)
    to words in Spanish

    Args:
        number (int): A positive number less than specified above
        mi_moneda(str,optional): A string in ISO 4217 short format
    Returns:
        A string in Spanish with first letters capitalized representing the number in letters

    Examples:
        >>> number_words(53625999567)
        'Cincuenta Y Tres Mil Seiscientos Venticinco Millones Novecientos Noventa Y Nueve Mil Quinientos Sesenta Y Siete'
    """
    if mi_moneda is not None:
        try:
            moneda = ifilter(lambda x: x['currency'] == mi_moneda, MONEDAS).next()
            if number < 2:
                moneda = moneda['singular']
            else:
                moneda = moneda['plural']
        except:
            return "Tipo de moneda inválida"
    else:
        moneda = ""

    human_readable = []
    num_units = format(number, ',').split(',')
    # print num_units
    for i, n in enumerate(num_units):
        if int(n) != 0:
            words = hundreds_word(int(n))
            units = UNITS[len(num_units) - i - 1][0 if int(n) == 1 else 1]
            human_readable.append([words, units])

    # filtrar MIL MILLONES - MILLONES -> MIL - MILLONES
    for i, item in enumerate(human_readable):
        try:
            if human_readable[i][1].find(human_readable[i + 1][1]):
                human_readable[i][1] = human_readable[i][1].replace(human_readable[i + 1][1], '')
        except IndexError:
            pass
    human_readable = [item for sublist in human_readable for item in sublist]
    human_readable.append(moneda)
    return ' '.join(human_readable).replace('  ', ' ').title().strip()


class account_invoice(models.Model):
    _name = "account.invoice"
    _inherit = "account.invoice"

    @api.one
    def _compute_bar_code(self):

        if self.type in ('in_invoice', 'in_refund'):
            return

        cuit = self.company_id.partner_id.vat
        pos = '0002'

        eivoucher_obj = self.env['wsfe.voucher_type']
        ei_voucher_type = eivoucher_obj.search([('document_type', '=', self.type), ('denomination_id', '=', self.denomination_id.id)])  # [0]

        if self.pos_ar_id:
            pos = self.pos_ar_id.name

        # ei_voucher_type = eivoucher_obj.browse(cr, uid, aux_res)
        inv_code = ei_voucher_type.code

        if self.state == 'open' and self.cae != 'NA' and self.cae_due_date:
            cae = self.cae
            cae_due_date = datetime.strptime(self.cae_due_date, '%Y-%m-%d')
        else:
            cae_due_date = datetime.now()
            cae = '0' * 14

        self.bar_code = cuit + '%02d' % int(inv_code) + pos + cae + cae_due_date.strftime('%Y%m%d') + '4'

    @api.one
    def _get_amount_to_text(self):
        parte_decimal = int(round(abs(self.amount_total) - abs(int(self.amount_total)), 2) * 100)
        if parte_decimal:
            amount_text = to_word(int(self.amount_total)).lower() + ' con ' + str(parte_decimal) + '/100'
        else:
            amount_text = to_word(int(self.amount_total)).lower()
        self.amount_text = amount_text

    amount_text = fields.Char(string='Amount text', readonly=True, compute=_get_amount_to_text)
    bar_code = fields.Char(string='Bar code', readonly=True, compute=_compute_bar_code)
