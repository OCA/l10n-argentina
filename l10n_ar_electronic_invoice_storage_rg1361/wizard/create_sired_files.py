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
import tempfile
import binascii, base64

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
        if int(invoice.fiscal_position.afip_code) == 5 and invoice.amount_total <= 1000.0:
            return ustr('%-30s') % 'CONSUMIDOR FINAL'

        val = ustr('%-30s') % invoice.partner_id.name
        partner_name = val[0:30]
        return partner_name


#    # TODO: Pasar a account.invoice en l10n_ar_point_of_sale esta funcion
#    # que tambien se puede utilizar desde electronic_invoice
#    def _get_amounts_and_vat_taxes(self, cr, uid, inv, ei_config):
#        iva_array = []
#
#        importe_neto = 0.0
#        importe_operaciones_exentas = 0.0
#        importe_iva = 0.0
#        importe_total = 0.0
#        importe_neto_no_gravado = 0.0
#
##        ei_config_obj = self.pool.get('electronic.invoice.config')
##        res = ei_config_obj.search(cr, uid, [('company_id', '=', inv.company_id.id)])
##        if not len(res):
##            raise osv.except_osv(_('Error'), _('Cannot find electronic invoice configuration for this company'))
##
##        ei_config = ei_config_obj.browse(cr, uid, res[0])
#
#        taxes = inv.tax_line
#        for tax in taxes:
#            for eitax in ei_config.vat_tax_ids+ei_config.exempt_operations_tax_ids:
#                if eitax.tax_code_id.id == tax.tax_code_id.id:
#                    if eitax.exempt_operations:
#                        importe_operaciones_exentas += tax.base
#                    else:
#                        importe_iva += tax.amount
#                        importe_neto += tax.base
#                        iva2 = {'Id': int(eitax.code), 'IVA': eitax.tax_id.amount, 'BaseImp': tax.base, 'Importe': tax.amount}
#                        iva_array.append(iva2)
#
#        importe_total = importe_neto + importe_neto_no_gravado + importe_operaciones_exentas + importe_iva
#        return importe_total, importe_neto, importe_neto_no_gravado, importe_operaciones_exentas, importe_iva, iva_array

    def _get_invoice_vat_taxes(self, cr, uid, invoice, context=None):
        # TODO: Cambiar esto. Lo mejor seria que el codigo de AFIP este en el mismo impuesto
        # y no tener que hacer este for que no tiene mucho sentido.
        wsfe_conf_obj = self.pool.get('wsfe.config')
        conf = wsfe_conf_obj.get_config(cr, uid)

        iva_array = []
        taxes = invoice.tax_line
        importe_neto = 0.0
        importe_iva = 0.0
        importe_tributos = 0.0

        for tax in taxes:
            found = False
            for eitax in conf.vat_tax_ids + conf.exempt_operations_tax_ids:
                if eitax.tax_code_id.id == tax.tax_code_id.id:
                    found = True
                    if eitax.exempt_operations:
                        pass
                    else:
                        importe_iva += tax.amount
                        importe_neto += tax.base
                        #iva2 = {'Id': int(eitax.code), 'BaseImp': tax.base, 'Importe': tax.amount}
                        iva2 = {'Id': int(eitax.code), 'IVA': eitax.tax_id.amount, 'BaseImp': tax.base, 'Importe': tax.amount}
                        iva_array.append(iva2)
            if not found:
                importe_tributos += tax.amount

        return iva_array

    def _get_operation_code(self, cr, uid, invoice):
        # TODO: Aca tendriamos que darle la opcion al usuario de que llene el codigo de operacion
        # Si el impuesto liquidado (campo 15) es igual a cero (0) y el importe total de conceptos que no integran el precio neto gravado (campo 13) es distinto de cero, se deberá completar de acuerdo con la siguiente codificación:
        # Z- Exportaciones a la zona franca.
        # X- Exportaciones al Exterior.
        # E- Operaciones Exentas.
        # N- No Gravado
        # En caso contrario se completará con espacios.
        if invoice.amount_tax == 0 and invoice.amount_no_taxed != 0:
            #raise osv.except_osv(_('Error'), _('You have to specify type of operation'))
            return 'E'
        return ' '

    def _get_voucher_type(self, cr, uid, invoice):
        eivoucher_obj = self.pool.get('electronic.invoice.voucher_type')
        denomination_id = invoice.denomination_id and invoice.denomination_id.id
        inv_type = invoice.type.split('_')[1]
        res = eivoucher_obj.search(cr, uid, [('document_type', 'like', inv_type), ('denomination_id', '=', denomination_id)])[0]
        ei_voucher_type = eivoucher_obj.browse(cr, uid, res)
        voucher_type = ei_voucher_type.code
        return voucher_type

    def _get_identifier_document_code_and_number(self, cr, uid, invoice):
        partner = invoice.partner_id
        if partner.document_type_id.afip_code == '99':
            if invoice.amount_total <= 1000:
                return '99', '0'*11
            else:
                raise osv.except_osv(_('SIRED Error!'), _('Cannot inform invoice %s%s because amount total is greater than 1000 and partner has not got document identification') % (invoice.denomination_id.name, invoice.internal_number))

        code = partner.document_type_id and partner.document_type_id.afip_code or False
        if not code or not partner.vat:
            raise osv.except_osv(_('SIRED Error!'), _('Cannot inform invoice %s%s because partner has not got document identification') % (invoice.denomination_id.name, invoice.internal_number))

        return code, partner.vat

    def _generate_head_file(self, cr, uid, company, period_id, period_name, invoice_ids, context):
        invoice_obj = self.pool.get('account.invoice')
        voucher_type_obj = self.pool.get('wsfe.voucher_type')

        importe_total_reg1 = 0.0
        importe_total_neto_no_gravado_reg1 = 0.0
        importe_total_neto_reg1 = 0.0
        importe_total_iva_reg1 = 0.0
        importe_total_operaciones_exentas_reg1 = 0.0

        head_regs = []
        for invoice in invoice_obj.browse(cr, uid, invoice_ids, context):
            type1_reg = []
            # Conversiones varias
            date_val = time.strptime(invoice.date_invoice, '%Y-%m-%d')
            date_invoice = time.strftime('%Y%m%d', date_val) # AAAAMMDD

            cae_due_date_val = time.strptime(invoice.cae_due_date, '%Y-%m-%d')
            cae_due_date = time.strftime('%Y%m%d', cae_due_date_val) # AAAAMMDD

            code, number = self._get_identifier_document_code_and_number(cr, uid, invoice)

            importe_total_reg1 += invoice.amount_total
            importe_total_neto_no_gravado_reg1 += invoice.amount_no_taxed
            importe_total_neto_reg1 += invoice.amount_taxed
            importe_total_iva_reg1 += invoice.amount_tax
            importe_total_operaciones_exentas_reg1 += invoice.amount_exempt

            pos_ar, invoice_number = invoice.internal_number.split('-')
            tipo_cbte = voucher_type_obj.get_voucher_type(cr, uid, invoice, context=context)

            # 'tipo_registro'
            type1_reg.append('1')
            # 'fecha_comprobante'
            type1_reg.append(date_invoice)
            # 'tipo_comprobante'
            #type1_reg.append(self._get_voucher_type(cr, uid, invoice))
            type1_reg.append(tipo_cbte)
            # 'controlador'
            type1_reg.append(' ')
            # 'punto_venta'
            type1_reg.append(pos_ar)
            # 'numero_comprobante'
            type1_reg.append(invoice_number)
            # 'numero_comprobante_reg'
            type1_reg.append(invoice_number)
            # 'cantidad_hojas'
            type1_reg.append('001')
            # 'codigo_doc_ident_comprador'
            type1_reg.append(code)
            # 'numero_ident_comprador'
            type1_reg.append(number)
            # 'apenom_comprador'
            type1_reg.append(self._get_partner_name(invoice))
            # 'importe_total'
            type1_reg.append(moneyfmt(Decimal(str(invoice.amount_total)), places=2, ndigits=15, dp='', sep=''))
            # 'neto_no_gravado'
            type1_reg.append(moneyfmt(Decimal(str(invoice.amount_no_taxed)), places=2, ndigits=15, dp='', sep=''))
            # 'neto_gravado'
            type1_reg.append(moneyfmt(Decimal(str(invoice.amount_taxed)), places=2, ndigits=15, dp='', sep=''))
            # 'impuesto_liquidado'
            type1_reg.append(moneyfmt(Decimal(str(invoice.amount_tax)), places=2, ndigits=15, dp='', sep=''))
            # 'impuesto_rni'
            type1_reg.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
            # 'impuesto_op_exentas'
            type1_reg.append(moneyfmt(Decimal(str(invoice.amount_exempt)), places=2, ndigits=15, dp='', sep=''))
            # 'percep_imp_nacionales'
            type1_reg.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
            # 'percep_iibb'
            type1_reg.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
            # 'percep_municipales'
            type1_reg.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
            # 'impuestos_internos'
            type1_reg.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
            # 'transporte'
            type1_reg.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
            # 'tipo_responsable'
            type1_reg.append(invoice.fiscal_position.afip_code)
            # 'codigo_moneda'
            type1_reg.append(invoice.currency_id.afip_code)
            # 'tipo_cambio'
            type1_reg.append(moneyfmt(Decimal('1.0'), places=6, ndigits=10, dp='', sep=''))
            # 'cant_alicuotas_iva'
            iva_array = self._get_invoice_vat_taxes(cr, uid, invoice, context)
            type1_reg.append(str(len(iva_array)))
            #type1_reg.append(len(iva_array) and str(len(iva_array)) or '1')
            # 'codigo_operacion'
            type1_reg.append(self._get_operation_code(cr,uid, invoice))
            # 'cae'
            type1_reg.append(invoice.cae)
            # 'fecha_vencimiento'
            type1_reg.append(cae_due_date)
            # 'fecha_anulacion'
            type1_reg.append(' '*8)

            # Apendeamos el registro
            head_regs.append(type1_reg)


        # Creacion del registro tipo 2 (Totales)
        company_cuit = company.partner_id.vat

        # head_type2_regs
        type2_reg = []

        # 'tipo_registro'
        type2_reg.append('2')
        # 'periodo'
        type2_reg.append(period_name)
        # 'relleno'
        type2_reg.append(' '*13)
        # Cantidad de registros tipo1
        type2_reg.append('%08d' % len(head_regs))
        # 'relleno'
        type2_reg.append(' '*17)
        # 'CUIT del Informante'
        type2_reg.append(company_cuit)
        # 'relleno'
        type2_reg.append(' '*22)
        # Importe total de la operacion
        type2_reg.append(moneyfmt(Decimal(str(importe_total_reg1)), places=2, ndigits=15, dp='', sep=''))
        # Importe total neto no gravado
        type2_reg.append(moneyfmt(Decimal(str(importe_total_neto_no_gravado_reg1)), places=2, ndigits=15, dp='', sep=''))
        # Importe total neto gravado
        type2_reg.append(moneyfmt(Decimal(str(importe_total_neto_reg1)), places=2, ndigits=15, dp='', sep=''))
        # Importe total impuesto liquidado
        type2_reg.append(moneyfmt(Decimal(str(importe_total_iva_reg1)), places=2, ndigits=15, dp='', sep=''))
        # Importe total impuesto liquidado RNI
        type2_reg.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # Importe total operaciones exentas
        type2_reg.append(moneyfmt(Decimal(str(importe_total_operaciones_exentas_reg1)), places=2, ndigits=15, dp='', sep=''))
        # Importe total percepciones nacionales
        type2_reg.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # Importe total percepciones iibb
        type2_reg.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # Importe total percepciones municipales
        type2_reg.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # Importe total impuestos internos
        type2_reg.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # 'relleno'
        type2_reg.append(' '*62)

        # Apendeamos el registro
        head_regs.append(type2_reg)


        head_filename = tempfile.mkstemp(suffix='.siredhead')[1]
        f = open(head_filename, 'w')

        for r in head_regs:
            r2 = [a.encode('utf-8') for a in r]
            try:
                f.write(''.join(r2))
            except Exception, e:
                raise e
            f.write('\r\n')

        f.close()

        f = open(head_filename, 'r')

        name = 'CABECERA_%s.txt' % period_name

        data_attach = {
            'name': name,
            'datas':binascii.b2a_base64(f.read()),
            'datas_fname': name,#name.replace('-', '_').replace('/', '_') + '.txt',
            #'description': '',
            'res_model': 'account.period',
            'res_id': period_id,
        }
        self.pool.get('ir.attachment').create(cr, uid, data_attach, context=context)
        f.close()

        return head_regs

    def _get_vat_tax_and_exempt_indicator(self, cr, uid, ei_config, line_taxes):

        # Tomamos la primer tax que encontremos en la configuracion
        # Evidentemente AFIP solo espera un IVA por linea por eso apenas
        # encontramos una que tenga codificacion, retornamos
        # TODO: Mejorar toda esta parte de impuestos de AFIP
        for tax in line_taxes:
            for eitax in ei_config.vat_tax_ids+ei_config.exempt_operations_tax_ids:
                if eitax.tax_code_id.id == tax.tax_code_id.id:
                    if eitax.exempt_operations:
                        return '0', 'E'
                    else:
                        return tax.amount*100, 'G'

    def _generate_detail_file(self, cr, uid, company, period_id, period_name, invoice_ids, context):
        invoice_obj = self.pool.get('account.invoice')

        ei_config_obj = self.pool.get('electronic.invoice.config')
        res = ei_config_obj.search(cr, uid, [('company_id', '=', company.id)])
        if not len(res):
            raise osv.except_osv(_('Error'), _('Cannot find electronic invoice configuration for this company'))

        ei_config = ei_config_obj.browse(cr, uid, res[0])

        detail_regs = []
        for invoice in invoice_obj.browse(cr, uid, invoice_ids, context):
            # Conversiones varias
            date_val = time.strptime(invoice.date_invoice, '%Y-%m-%d')
            date_invoice = time.strftime('%Y%m%d', date_val) # AAAAMMDD

            for line in invoice.invoice_line:
                reg = []
                # 'tipo_comprobante'
                reg.append(self._get_voucher_type(cr, uid, invoice))
                # 'controlador'
                reg.append(' ')
                # 'fecha_comprobante'
                reg.append(date_invoice)
                # 'punto_venta'
                reg.append(invoice.pos_ar_id.name)
                # 'numero_comprobante'
                reg.append(invoice.internal_number)
                # 'numero_comprobante_reg'
                reg.append(invoice.internal_number)
                # Cantidad
                reg.append(moneyfmt(Decimal(str(line.quantity)), places=5, ndigits=12, dp='', sep=''))
                # Unidad de Medida
                reg.append(line.uos_id.afip_code)
                # Precio Unitario
                reg.append(moneyfmt(Decimal(str(line.price_unit)), places=3, ndigits=16, dp='', sep=''))
                # Importe de Bonificacion
                # TODO: Tener en cuenta los descuentos
                reg.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
                # Importe de ajuste
                reg.append(moneyfmt(Decimal('0.0'), places=3, ndigits=16, dp='', sep=''))
                # Subtotal por registro
                reg.append(moneyfmt(Decimal(str(line.price_subtotal)), places=3, ndigits=16, dp='', sep=''))
                # Alicuota de IVA
                iva, exempt_indicator = self._get_vat_tax_and_exempt_indicator(cr, uid, ei_config, line.invoice_line_tax_id)
                reg.append(moneyfmt(Decimal(str(iva)), places=2, ndigits=4, dp='', sep=''))
                # Indicacion de Exento, Gravado o No Gravado
                # TODO: Tenemos que tener en cuenta los casos en que son exentos
                reg.append('G')
                # Indicacion de Anulacion
                reg.append(' ')
                # Disenio Libre
                product_name = ustr('%-75s') % line.name

                reg.append(product_name)
                #reg.append("\r\n")
                # Apendeamos el registro
                detail_regs.append(reg)


        detail_filename = tempfile.mkstemp(suffix='.sireddetail')[1]
        f = open(detail_filename, 'w')

        for r in detail_regs:
            # TODO: Quitar esto. Si lo hacemos en el append de mas arriba
            # no funciona. Aca si, averiguar por que
            r2 = [a.encode('utf-8') for a in r]
            f.write(''.join(r2))
            f.write('\r\n')

        f.close()

        f = open(detail_filename, 'r')
        name = 'DETALLE_%s.txt' % period_name
        data_attach = {
            'name': name,
            'datas':binascii.b2a_base64(f.read()),
            'datas_fname': name,#name.replace('-', '_').replace('/', '_') + '.txt',
            #'description': '',
            'res_model': 'account.period',
            'res_id': period_id,
        }
        self.pool.get('ir.attachment').create(cr, uid, data_attach, context=context)
        f.close()

        return detail_regs

    def _generate_sales_file(self, cr, uid, company, period_id, period_name, invoice_ids, context):
        invoice_obj = self.pool.get('account.invoice')
        ei_config_obj = self.pool.get('electronic.invoice.config')

        res = ei_config_obj.search(cr, uid, [('company_id', '=', company.id)])
        if not len(res):
            raise osv.except_osv(_('Error'), _('Cannot find electronic invoice configuration for this company'))

        ei_config = ei_config_obj.browse(cr, uid, res[0])

        importe_total_reg1 = 0.0
        importe_total_neto_no_gravado_reg1 = 0.0
        importe_total_neto_reg1 = 0.0
        importe_total_iva_reg1 = 0.0
        importe_total_operaciones_exentas_reg1 = 0.0

        sale_regs = []
        for invoice in invoice_obj.browse(cr, uid, invoice_ids, context):

            # Conversiones varias
            date_val = time.strptime(invoice.date_invoice, '%Y-%m-%d')
            date_invoice = time.strftime('%Y%m%d', date_val) # AAAAMMDD

            cae_due_date_val = time.strptime(invoice.cae_due_date, '%Y-%m-%d')
            cae_due_date = time.strftime('%Y%m%d', cae_due_date_val) # AAAAMMDD

            code, number = self._get_identifier_document_code_and_number(cr, uid, invoice)

            importe_total, importe_neto, importe_neto_no_gravado, importe_operaciones_exentas, importe_iva, iva_array = self._get_amounts_and_vat_taxes(cr, uid, invoice, ei_config)

            # Importe total de todos los registros 1
            importe_total_reg1 += importe_total
            importe_total_neto_no_gravado_reg1 += importe_neto_no_gravado
            importe_total_neto_reg1 += importe_neto
            importe_total_iva_reg1 += importe_iva
            importe_total_operaciones_exentas_reg1 += importe_operaciones_exentas

            for alic_iva in iva_array:
                sale_reg_type1 = []

                # 'tipo_registro' (1)
                sale_reg_type1.append('1')
                # 'fecha_comprobante' (2)
                sale_reg_type1.append(date_invoice)
                # 'tipo_comprobante' (3)
                sale_reg_type1.append(self._get_voucher_type(cr, uid, invoice))
                # 'controlador' (4)
                sale_reg_type1.append(' ')
                # 'punto_venta' (5)
                sale_reg_type1.append(invoice.pos_ar_id.name)
                # 'numero_comprobante' (6)
                sale_reg_type1.append(invoice.internal_number)
                # 'numero_comprobante_reg' (7)
                sale_reg_type1.append(invoice.internal_number)
                # 'codigo_doc_ident_comprador' (8)
                sale_reg_type1.append(code)
                # 'numero_ident_comprador' (9)
                sale_reg_type1.append(number)
                # 'apenom_comprador' (10)
                sale_reg_type1.append(self._get_partner_name(invoice))

                # 'importe_total' (11)
                sale_reg_type1.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
                #sale_reg_type1.append(moneyfmt(Decimal(importe_total), places=2, ndigits=15, dp='', sep=''))

                # 'neto_no_gravado' (12)
                sale_reg_type1.append(moneyfmt(Decimal(str(importe_neto_no_gravado)), places=2, ndigits=15, dp='', sep=''))
                # 'neto_gravado' (13)
                sale_reg_type1.append(moneyfmt(Decimal(str(alic_iva['BaseImp'])), places=2, ndigits=15, dp='', sep=''))

                # Alicuota de IVA (14)
                sale_reg_type1.append(str(alic_iva['Id']))

                # 'impuesto_liquidado' (15)
                sale_reg_type1.append(moneyfmt(Decimal(str(alic_iva['Importe'])), places=2, ndigits=15, dp='', sep=''))
                # 'impuesto_rni' (16)
                sale_reg_type1.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
                # 'impuesto_op_exentas' (17)
                sale_reg_type1.append(moneyfmt(Decimal(str(importe_operaciones_exentas)), places=2, ndigits=15, dp='', sep=''))
                # 'percep_imp_nacionales' (18)
                sale_reg_type1.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
                # 'percep_iibb' (19)
                sale_reg_type1.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
                # 'percep_municipales' (20)
                sale_reg_type1.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
                # 'impuestos_internos' (21)
                sale_reg_type1.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
                # 'tipo_responsable' (22)
                sale_reg_type1.append(invoice.fiscal_position.afip_code)
                # 'codigo_moneda' (23)
                sale_reg_type1.append(invoice.currency_id.afip_code)
                # 'tipo_cambio' (24)
                sale_reg_type1.append(moneyfmt(Decimal('1.0'), places=6, ndigits=10, dp='', sep=''))
                # 'cant_alicuotas_iva' (25)
                sale_reg_type1.append(len(iva_array) and str(len(iva_array)) or '1')
                # 'codigo_operacion' (26)
                sale_reg_type1.append(self._get_operation_code(cr,uid, invoice))
                # 'cae' (27)
                sale_reg_type1.append(invoice.cae)
                # 'fecha_vencimiento' (28)
                sale_reg_type1.append(cae_due_date)
                # 'fecha_anulacion' (29)
                sale_reg_type1.append(' '*8)

                # 'Informacion Adicional' (30)
                # TODO: Ibamos a poner los comentarios de la Factura, pero son mas internos
                sale_reg_type1.append(' '*75)

                # Apendeamos el registro
                sale_regs.append(sale_reg_type1)

            # En el ultimo reg1 consignamos valores totales segun la RG
            sale_reg_type1[10] = moneyfmt(Decimal(str(importe_total)), places=2, ndigits=15, dp='', sep='')


        # Creacion del registro tipo 2 (Totales)
        company_cuit = company.partner_id.vat

        # Registros de Ventas Tipo 2
        sale_reg_type2 = []

        # 'tipo_registro'
        sale_reg_type2.append('2')
        # 'periodo'
        sale_reg_type2.append(period_name)
        # 'relleno'
        sale_reg_type2.append(' '*29)
        # Cantidad de registros tipo1
        sale_reg_type2.append('%012d' % len(sale_regs))
        # 'relleno'
        sale_reg_type2.append(' '*30)
        # 'CUIT del Informante'
        sale_reg_type2.append(company_cuit)
        # 'relleno'
        sale_reg_type2.append(' '*30)
        # Importe total de la operacion
        sale_reg_type2.append(moneyfmt(Decimal(str(importe_total_reg1)), places=2, ndigits=15, dp='', sep=''))
        # Importe total neto no gravado
        sale_reg_type2.append(moneyfmt(Decimal(str(importe_total_neto_no_gravado_reg1)), places=2, ndigits=15, dp='', sep=''))
        # Importe total neto gravado
        sale_reg_type2.append(moneyfmt(Decimal(str(importe_total_neto_reg1)), places=2, ndigits=15, dp='', sep=''))
        # 'relleno'
        sale_reg_type2.append(' '*4)
        # Importe total impuesto liquidado
        sale_reg_type2.append(moneyfmt(Decimal(str(importe_total_iva_reg1)), places=2, ndigits=15, dp='', sep=''))
        # Importe total impuesto liquidado RNI
        sale_reg_type2.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # Importe total operaciones exentas
        sale_reg_type2.append(moneyfmt(Decimal(str(importe_total_operaciones_exentas_reg1)), places=2, ndigits=15, dp='', sep=''))
        # Importe total percepciones nacionales
        sale_reg_type2.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # Importe total percepciones iibb
        sale_reg_type2.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # Importe total percepciones municipales
        sale_reg_type2.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # Importe total impuestos internos
        sale_reg_type2.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # 'relleno'
        sale_reg_type2.append(' '*122)

        # Apendeamos el registro
        sale_regs.append(sale_reg_type2)

        sale_filename = tempfile.mkstemp(suffix='.siredsale')[1]
        f = open(sale_filename, 'w')

        for r in sale_regs:
            # TODO: Quitar esto. Si lo hacemos en el append de mas arriba
            # no funciona. Aca si, averiguar por que
            r2 = [a.encode('utf-8') for a in r]
            f.write(''.join(r2))
            f.write('\r\n')

        f.close()

        f = open(sale_filename, 'r')
        name = 'VENTAS_%s.txt' % period_name
        data_attach = {
            'name': name,
            'datas':binascii.b2a_base64(f.read()),
            'datas_fname': name,#name.replace('-', '_').replace('/', '_') + '.txt',
            #'description': '',
            'res_model': 'account.period',
            'res_id': period_id,
        }
        self.pool.get('ir.attachment').create(cr, uid, data_attach, context=context)
        f.close()

        return sale_regs


    def _generate_purchase_file(self, cr, uid, company, period_id, period_name, invoice_ids, context):
        invoice_obj = self.pool.get('account.invoice')
        ei_config_obj = self.pool.get('electronic.invoice.config')

        res = ei_config_obj.search(cr, uid, [('company_id', '=', company.id)])
        if not len(res):
            raise osv.except_osv(_('Error'), _('Cannot find electronic invoice configuration for this company'))

        ei_config = ei_config_obj.browse(cr, uid, res[0])

        importe_total_reg1 = 0.0
        importe_total_neto_no_gravado_reg1 = 0.0
        importe_total_neto_reg1 = 0.0
        importe_total_iva_reg1 = 0.0
        importe_total_operaciones_exentas_reg1 = 0.0

        purchase_regs = []
        for invoice in invoice_obj.browse(cr, uid, invoice_ids, context):

            # Conversiones varias
            date_val = time.strptime(invoice.date_invoice, '%Y-%m-%d')
            date_invoice = time.strftime('%Y%m%d', date_val) # AAAAMMDD

            cae_due_date = '2013-01-01'
            #cae_due_date_val = time.strptime(invoice.cae_due_date, '%Y-%m-%d')
            #cae_due_date = time.strftime('%Y%m%d', cae_due_date_val) # AAAAMMDD

            code, number = self._get_identifier_document_code_and_number(cr, uid, invoice)

            pos, invoice_number = invoice.internal_number.split('-')

            importe_total, importe_neto, importe_neto_no_gravado, importe_operaciones_exentas, importe_iva, iva_array = self._get_amounts_and_vat_taxes(cr, uid, invoice, ei_config)

            # Importe total de todos los registros 1
            importe_total_reg1 += importe_total
            importe_total_neto_no_gravado_reg1 += importe_neto_no_gravado
            importe_total_neto_reg1 += importe_neto
            importe_total_iva_reg1 += importe_iva
            importe_total_operaciones_exentas_reg1 += importe_operaciones_exentas

            for alic_iva in iva_array:
                purchase_reg_type1 = []

                # 'tipo_registro' (1)
                purchase_reg_type1.append('1')
                # 'fecha_comprobante' (2)
                purchase_reg_type1.append(date_invoice)
                # 'tipo_comprobante' (3)
                purchase_reg_type1.append(self._get_voucher_type(cr, uid, invoice))
                # 'controlador' (4)
                purchase_reg_type1.append(' ')
                # 'punto_venta' (5)
                purchase_reg_type1.append(pos)
                # 'numero_comprobante' (6)
                purchase_reg_type1.append(invoice_number)
                # 'Fecha de Registracion Contable' (7)
                # TODO: Por ahora es date_invoice, despues lo cambiaremos
                purchase_reg_type1.append(date_invoice)
                # 'Codigo de Aduana' (8)
                purchase_reg_type1.append(' '*3)
                # 'Codigo de Destinacion' (9)
                purchase_reg_type1.append(' '*4)
                # 'Numero de despacho' (10)
                purchase_reg_type1.append(' '*6)
                # 'Digito verificador del numero de despacho' (11)
                purchase_reg_type1.append(' ')
                # 'Codigo de documento identificatorio del Vendedor' (12)
                purchase_reg_type1.append(code)
                # 'Numero identificatorio Vendedor' (13)
                purchase_reg_type1.append(number)
                # 'Apellido y nombre del Vendedor' (14)
                purchase_reg_type1.append(self._get_partner_name(invoice))
                # 'importe_total' (15)
                purchase_reg_type1.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
                # 'neto_no_gravado' (16)
                purchase_reg_type1.append(moneyfmt(Decimal(str(importe_neto_no_gravado)), places=2, ndigits=15, dp='', sep=''))
                # 'neto_gravado' (17)
                purchase_reg_type1.append(moneyfmt(Decimal(str(alic_iva['BaseImp'])), places=2, ndigits=15, dp='', sep=''))
                # Alicuota de IVA (18)
                purchase_reg_type1.append(str(alic_iva['Id']))
                # 'impuesto_liquidado' (19)
                purchase_reg_type1.append(moneyfmt(Decimal(str(alic_iva['Importe'])), places=2, ndigits=15, dp='', sep=''))
                # 'Importe de Operaciones Exentas' (20)
                purchase_reg_type1.append(moneyfmt(Decimal(str(importe_operaciones_exentas)), places=2, ndigits=15, dp='', sep=''))
                # 'Importe de percepciones o pagos a cuenta del IVA' (21)
                purchase_reg_type1.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
                # 'Importe de percepciones o pagos a cuenta de otros impuestos nacionales' (22)
                purchase_reg_type1.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
                # 'Importe de percepciones de IIBB' (23)
                purchase_reg_type1.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
                # 'Importe de percepciones de Impuestos Municipales' (24)
                purchase_reg_type1.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
                # 'Importe de Impuestos Internos' (25)
                purchase_reg_type1.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
                # 'tipo_responsable' (26)
                purchase_reg_type1.append(invoice.fiscal_position.afip_code)
                # 'codigo_moneda' (27)
                purchase_reg_type1.append(invoice.currency_id.afip_code)
                # 'tipo_cambio' (28)
                purchase_reg_type1.append(moneyfmt(Decimal('1.0'), places=6, ndigits=10, dp='', sep=''))
                # 'cant_alicuotas_iva' (29)
                purchase_reg_type1.append(len(iva_array) and str(len(iva_array)) or '1')
                # 'codigo_operacion' (30)
                purchase_reg_type1.append(self._get_operation_code(cr,uid, invoice))
                # 'cae' (31)
                purchase_reg_type1.append(invoice.cae or '123123123123')
                # 'fecha_vencimiento' (32)
                purchase_reg_type1.append(cae_due_date)
                # 'Informacion Adicional' (33)
                # TODO: Ibamos a poner los comentarios de la Factura, pero son mas internos
                purchase_reg_type1.append(' '*75)

                # Apendeamos el registro
                purchase_regs.append(purchase_reg_type1)

            # En el ultimo reg1 consignamos valores totales segun la RG
            # TODO: Agregar los de percepciones que tambien todos se consignan en el ultimo de los registros
            purchase_reg_type1[10] = moneyfmt(Decimal(str(importe_total)), places=2, ndigits=15, dp='', sep='')


        # Creacion del registro tipo 2 (Totales)
        company_cuit = company.partner_id.vat

        # Registros de Ventas Tipo 2
        purchase_reg_type2 = []

        # 'Tipo de Registro' (1)
        purchase_reg_type2.append('2')
        # 'Periodo' (2)
        purchase_reg_type2.append(period_name)
        # 'Relleno' (3)
        purchase_reg_type2.append(' '*29)
        # Cantidad de registros tipo1 (4)
        purchase_reg_type2.append('%012d' % len(purchase_regs))
        # 'relleno' (5)
        purchase_reg_type2.append(' '*31)
        # 'CUIT del Informante' (6)
        purchase_reg_type2.append(company_cuit)
        # 'relleno' (7)
        purchase_reg_type2.append(' '*30)
        # Importe total de la operacion (8)
        purchase_reg_type2.append(moneyfmt(Decimal(str(importe_total_reg1)), places=2, ndigits=15, dp='', sep=''))
        # Importe total neto no gravado (9)
        purchase_reg_type2.append(moneyfmt(Decimal(str(importe_total_neto_no_gravado_reg1)), places=2, ndigits=15, dp='', sep=''))
        # Importe total neto gravado (10)
        purchase_reg_type2.append(moneyfmt(Decimal(str(importe_total_neto_reg1)), places=2, ndigits=15, dp='', sep=''))
        # 'relleno' (11)
        purchase_reg_type2.append(' '*4)
        # Importe total impuesto liquidado (12)
        purchase_reg_type2.append(moneyfmt(Decimal(str(importe_total_iva_reg1)), places=2, ndigits=15, dp='', sep=''))
        # Importe total operaciones exentas (13)
        purchase_reg_type2.append(moneyfmt(Decimal(str(importe_total_operaciones_exentas_reg1)), places=2, ndigits=15, dp='', sep=''))
        # Importe total percepciones o pagos a cuenta del IVA (14)
        purchase_reg_type2.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # Importe total percepciones o pagos a cuenta de otros impuestos nacionales (15)
        purchase_reg_type2.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # Importe total percepciones de IIBB (16)
        purchase_reg_type2.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # Importe total percepciones de impuestos internos (17)
        purchase_reg_type2.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # Importe total impuestos internos (17)
        purchase_reg_type2.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
        # 'relleno' (19)
        purchase_reg_type2.append(' '*114)

        # Apendeamos el registro
        purchase_regs.append(purchase_reg_type2)

        purchase_filename = tempfile.mkstemp(suffix='.siredpurchase')[1]
        f = open(purchase_filename, 'w')

        for r in purchase_regs:
            # TODO: Quitar esto. Si lo hacemos en el append de mas arriba
            # no funciona. Aca si, averiguar por que
            r2 = [a.encode('utf-8') for a in r]
            f.write(''.join(r2))
            f.write('\r\n')

        f.close()

        f = open(purchase_filename, 'r')
        name = 'COMPRAS_%s.txt' % period_name
        data_attach = {
            'name': name,
            'datas':binascii.b2a_base64(f.read()),
            'datas_fname': name,#name.replace('-', '_').replace('/', '_') + '.txt',
            #'description': '',
            'res_model': 'account.period',
            'res_id': period_id,
        }
        self.pool.get('ir.attachment').create(cr, uid, data_attach, context=context)
        f.close()

        return purchase_regs




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
        company = period.company_id

        # Buscamos las facturas del periodo pedido
        # ordenados segun lo escrito en la RG1361/1492
        #invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('period_id','=',period.id), ('state','in', ('open', 'paid'))], context=context)
        
        invoice_query = "SELECT i.id " \
        "FROM account_invoice i " \
        "JOIN account_period p on p.id=i.period_id " \
        "JOIN invoice_denomination d on d.id=i.denomination_id " \
        "JOIN pos_ar pos on pos.id=i.pos_ar_id " \
        "JOIN res_partner par on par.id=i.partner_id, wsfe_voucher_type wvt " \
        "WHERE p.id=%(period)s AND wvt.denomination_id=i.denomination_id " \
        "AND i.state in %(state)s " \
        "AND ((wvt.document_type='out_debit' AND i.is_debit_note='t') OR (wvt.document_type=i.type AND i.is_debit_note='f')) " \
        "AND i.type in %(invoice_types)s " \
        "ORDER BY i.date_invoice, wvt.code, pos.name, i.internal_number "

        cr.execute(invoice_query, {'period': period.id, 'state': ('open', 'paid',), 'invoice_types': ('out_invoice', 'out_refund',)})
        res = cr.fetchall()
        invoice_ids = [ids[0] for ids in res]

        period_split = period.code.split('/')
        period_name = period_split[1]+period_split[0]

        # Generamos los registros de Cabecera Tipo 1 y Tipo 2
        self._generate_head_file(cr, uid, company, period.id, period_name, invoice_ids, context)

        # Generamos los registros de Detalle Tipo 1
        #self._generate_detail_file(cr, uid, company, period.id, period_name, invoice_ids, context)

        # Generamos los registros de Ventas Tipo 1 y Tipo 2
        #self._generate_sales_file(cr, uid, company, period.id, period_name, invoice_ids, context)

#        # Generamos los registros de Compras Tipo 1 y Tipo 2
#        purchase_invoice_query = "SELECT i.id " \
#        "FROM account_invoice i " \
#        "JOIN account_period p on p.id=i.period_id " \
#        "JOIN invoice_denomination d on d.id=i.denomination_id " \
#        "JOIN res_partner par on par.id=i.partner_id, electronic_invoice_voucher_type evt " \
#        "WHERE p.id=%(period)s AND evt.denomination_id=i.denomination_id " \
#        "AND i.state in %(state)s " \
#        "AND i.type in %(invoice_types)s " \
#        "ORDER BY i.date_invoice, i.internal_number "
#
#        cr.execute(purchase_invoice_query, {'period': period.id, 'state': ('open', 'paid',), 'invoice_types': ('in_invoice', 'in_refund',)})
#        res = cr.fetchall()
#        invoice_ids = [ids[0] for ids in res]
#
#        # Generamos los registros de Compras
#        self._generate_purchase_file(cr, uid, company, period.id, period_name, invoice_ids, context)


        return {'type': 'ir.actions.act_window_close'}

create_sired_files()
