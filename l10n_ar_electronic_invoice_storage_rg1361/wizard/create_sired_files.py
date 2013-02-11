# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-2013 E-MIPS Electronica e Informatica
#               All Rights Reserved (<http://www.e-mips.com.ar>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
from tools.translate import _
from tools.misc import ustr
import time
from decimal import *

def moneyfmt(value, places=2, ndigits=15, curr='', sep=',', dp='.',
             pos='', neg='-', trailneg=''):
    """Convert Decimal to a money formatted string.

    places:  required number of places after the decimal point
    curr:    optional currency symbol before the sign (may be blank)
    sep:     optional grouping separator (comma, period, space, or blank)
    dp:      decimal point indicator (comma or period)
             only specify as blank when places is zero
    pos:     optional sign for positive numbers: '+', space or blank
    neg:     optional sign for negative numbers: '-', '(', space or blank
    trailneg:optional trailing minus indicator:  '-', ')', space or blank

    >>> d = Decimal('-1234567.8901')
    >>> moneyfmt(d, curr='$')
    '-$1,234,567.89'
    >>> moneyfmt(d, places=0, sep='.', dp='', neg='', trailneg='-')
    '1.234.568-'
    >>> moneyfmt(d, curr='$', neg='(', trailneg=')')
    '($1,234,567.89)'
    >>> moneyfmt(Decimal(123456789), sep=' ')
    '123 456 789.00'
    >>> moneyfmt(Decimal('-0.02'), neg='<', trailneg='>')
    '<0.02>'

    """
    q = Decimal(10) ** -places      # 2 places --> '0.01'
    sign, digits, exp = value.quantize(q).as_tuple()
    result = []
    digits = map(str, digits)
    digits_total = 0
    build, next = result.append, digits.pop
    if sign:
        build(trailneg)
    for i in range(places):
        build(next() if digits else '0')
        digits_total += 1
    build(dp)
    if not digits:
        build('0')
        digits_total += 1
    i = 0
    while digits:
        build(next())
        digits_total += 1
        i += 1
        if i == 3 and digits:
            i = 0
            build(sep)
    # Si le faltan digitos, rellenamos con ceros
    for i in range(ndigits-digits_total):
        build('0')
    build(curr)
    build(neg if sign else pos)
    return ''.join(reversed(result))



class create_sired_files(osv.osv_memory):
    _name = 'create.sired.files'
    _description = 'Wizard Create Sired Files'

    _columns = {
        'period_id': fields.many2one('account.period', 'Period'),
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}

        res = super(create_sired_files, self).default_get(cr, uid, fields, context=context)

        if context.get('active_model') == 'account.period':
            res['period_id'] = context.get('active_id', False)

        return res


    def _get_partner_name(self, invoice):
        # El nombre del partner se corta en 30 o se le agregan espacios para completar
        # TODO: HORRIBLE, cambiar esto URGENTE!!!! No se puede chequear asi esto
        if invoice.fiscal_position.name == 'Consumidor Final':
            if invoice.amount_total <= 1000.0:
                return ustr('%30s') % 'CONSUMIDOR FINAL'
            else:
                raise osv.except_osv(_('Error!'), _('Cannot get identifier document for partner %s') % invoice.partner_id.name)

        val = ustr('%30s') % invoice.partner_id.name
        partner_name = val[0:30]
        return partner_name


    # TODO: Pasar a account.invoice en l10n_ar_point_of_sale esta funcion
    # que tambien se puede utilizar desde electronic_invoice
    def _get_amounts_and_vat_taxes(self, cr, uid, inv):
        iva_array = []

        importe_neto = 0.0
        importe_operaciones_exentas = 0.0
        importe_iva = 0.0
        importe_total = 0.0
        importe_neto_no_gravado = 0.0

        # PRUEBA
        #import pdb
        #pdb.set_trace()
        ei_config_obj = self.pool.get('electronic.invoice.config')
        res = ei_config_obj.search(cr, uid, [('company_id', '=', inv.company_id.id)])
        if not len(res):
            raise osv.except_osv(_('Error'), _('Cannot find electronic invoice configuration for this company'))

        ei_config = ei_config_obj.browse(cr, uid, res[0])

        taxes = inv.tax_line
        for tax in taxes:
            for eitax in ei_config.vat_tax_ids+ei_config.exempt_operations_tax_ids:
                if eitax.tax_code_id.id == tax.tax_code_id.id:
                    if eitax.exempt_operations:
                        importe_operaciones_exentas += tax.base
                    else:
                        importe_iva += tax.amount
                        importe_neto += tax.base
                        iva2 = {'Id': int(eitax.code), 'BaseImp': tax.base, 'Importe': tax.amount}
                        iva_array.append(iva2)

        importe_total = importe_neto + importe_neto_no_gravado + importe_operaciones_exentas + importe_iva
        return importe_total, importe_neto, importe_neto_no_gravado, importe_operaciones_exentas, importe_iva, iva_array

    def _get_operation_code(self, cr, uid, importe_iva, neto_no_gravado, invoice):
        if importe_iva == 0 and neto_no_gravado != 0:
            raise osv.except_osv(_('Error'), _('You have to specify type of operation'))
        return ' '

    def _get_voucher_type(self, cr, uid, invoice):
        eivoucher_obj = self.pool.get('electronic.invoice.voucher_type')
        denomination_id = invoice.denomination_id and invoice.denomination_id.id
        res = eivoucher_obj.search(cr, uid, [('document_type', '=', invoice.type), ('denomination_id', '=', denomination_id)])[0]
        ei_voucher_type = eivoucher_obj.browse(cr, uid, res)
        voucher_type = ei_voucher_type.code
        return voucher_type

    def _get_identifier_document_code_and_number(self, cr, uid, invoice):
        partner = invoice.partner_id
        # TODO: Deberiamos agregar tipo de documento
        if partner.vat:
            return '80', partner.vat
        else:
            if invoice.amount_total<=1000:
                return '99', '0'*11
            else:
                raise osv.except_osv(_('SIRED Error!'), _('Cannot inform invoice %s%s-%s because amount total is greater than 1000 and partner has not got document identification') % (invoice.denomination_id.name, invoice.pos_ar_id.name, invoice.internal_number))


    def _generate_head_file(self, cr, uid, invoice_ids, context):
        invoice_obj = self.pool.get('account.invoice')

        head_type1_regs = []
        print 'invoice_ids: ', invoice_ids
        for invoice in invoice_obj.browse(cr, uid, invoice_ids, context):
            type1_reg = {}
            # Conversiones varias
            date_val = time.strptime(invoice.date_invoice, '%Y-%m-%d')
            date_invoice = time.strftime('%Y%m%d', date_val) # AAAAMMDD

            cae_due_date_val = time.strptime(invoice.cae_due_date, '%Y-%m-%d')
            cae_due_date = time.strftime('%Y%m%d', cae_due_date_val) # AAAAMMDD

            code, number = self._get_identifier_document_code_and_number(cr, uid, invoice)

            importe_total, importe_neto, importe_neto_no_gravado, importe_operaciones_exentas, importe_iva, iva_array = self._get_amounts_and_vat_taxes(cr, uid, invoice)

            type1_reg['tipo_registro'] = '1'
            type1_reg['fecha_comprobante'] = date_invoice
            type1_reg['tipo_comprobante'] = self._get_voucher_type(cr, uid, invoice)
            type1_reg['controlador'] = ' '
            type1_reg['punto_venta'] = invoice.pos_ar_id.name
            type1_reg['numero_comprobante'] = invoice.internal_number
            type1_reg['numero_comprobante_reg'] = invoice.internal_number
            type1_reg['cantidad_hojas'] = '001'
            type1_reg['codigo_doc_ident_comprador'] = code
            type1_reg['numero_ident_comprador'] = number
            type1_reg['apenom_comprador'] = self._get_partner_name(invoice)
            type1_reg['importe_total'] = moneyfmt(Decimal(importe_total), places=2, ndigits=15, dp='', sep='')
            type1_reg['neto_no_gravado'] = moneyfmt(Decimal(importe_neto_no_gravado), places=2, ndigits=15, dp='', sep='')
            type1_reg['neto_gravado'] = moneyfmt(Decimal(importe_neto), places=2, ndigits=15, dp='', sep='')
            type1_reg['impuesto_liquidado'] = moneyfmt(Decimal(importe_iva), places=2, ndigits=15, dp='', sep='')
            type1_reg['impuesto_rni'] = moneyfmt(Decimal(0.0), places=2, ndigits=15, dp='', sep='')
            type1_reg['impuesto_op_exentas'] = moneyfmt(Decimal(importe_operaciones_exentas), places=2, ndigits=15, dp='', sep='')
            type1_reg['percep_imp_nacionales'] = moneyfmt(Decimal(0.0), places=2, ndigits=15, dp='', sep='')
            type1_reg['percep_iibb'] = moneyfmt(Decimal(0.0), places=2, ndigits=15, dp='', sep='')
            type1_reg['percep_municipales'] = moneyfmt(Decimal(0.0), places=2, ndigits=15, dp='', sep='')
            type1_reg['impuestos_internos'] = moneyfmt(Decimal(0.0), places=2, ndigits=15, dp='', sep='')
            type1_reg['transporte'] = moneyfmt(Decimal(0.0), places=2, ndigits=15, dp='', sep='')
            type1_reg['tipo_responsable'] = invoice.fiscal_position.afip_code
            type1_reg['codigo_moneda'] = invoice.currency_id.afip_code
            type1_reg['tipo_cambio'] = moneyfmt(Decimal(1.0), places=6, ndigits=10, dp='', sep='')
            type1_reg['cant_alicuotas_iva'] = len(iva_array) or '1'
            type1_reg['codigo_operacion'] = self._get_operation_code(cr,uid, importe_iva, importe_neto_no_gravado, invoice)
            type1_reg['cae'] = invoice.aut_cae
            type1_reg['cae'] = invoice.aut_cae
            type1_reg['fecha_vencimiento'] = cae_due_date
            type1_reg['fecha_anulacion'] = '0'*8

            # Apendeamos el registro
            head_type1_regs.append(type1_reg)

    def create_files(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """
        data = self.browse(cr, uid, ids, context)[0]

        period = data.period_id

        # Buscamos las facturas del periodo pedido
        invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('period_id','=',period.id), ('state','in', ('open', 'paid'))], context=context)
        
        self._generate_head_file(cr, uid, invoice_ids, context)

        return {'type': 'ir.actions.act_window_close'}

create_sired_files()
