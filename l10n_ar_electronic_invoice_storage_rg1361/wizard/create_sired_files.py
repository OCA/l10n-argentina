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
        # TODO: HORRIBLE, cambiar esto URGENTE!!!! No se puede chequear asi esto
        if invoice.fiscal_position.name == 'Consumidor Final':
            if invoice.amount_total <= 1000.0:
                return ustr('%-30s') % 'CONSUMIDOR FINAL'
            elif invoice.partner_id.vat:
                val = ustr('%-30s') % invoice.partner_id.name
                partner_name = val[0:30]
                return partner_name
            else:
                raise osv.except_osv(_('Error!'), _('Cannot get identifier document for partner %s') % invoice.partner_id.name)

        val = ustr('%-30s') % invoice.partner_id.name
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
                        iva2 = {'Id': int(eitax.code), 'IVA': eitax.tax_id.amount, 'BaseImp': tax.base, 'Importe': tax.amount}
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

    def _generate_head_file(self, cr, uid, company, period_id, period_name, invoice_ids, context):
        invoice_obj = self.pool.get('account.invoice')

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

            importe_total, importe_neto, importe_neto_no_gravado, importe_operaciones_exentas, importe_iva, iva_array = self._get_amounts_and_vat_taxes(cr, uid, invoice)
            importe_total_reg1 += importe_total
            importe_total_neto_no_gravado_reg1 += importe_neto_no_gravado
            importe_total_neto_reg1 += importe_neto
            importe_total_iva_reg1 += importe_iva
            importe_total_operaciones_exentas_reg1 += importe_operaciones_exentas

            # 'tipo_registro'
            type1_reg.append('1')
            # 'fecha_comprobante'
            type1_reg.append(date_invoice)
            # 'tipo_comprobante'
            type1_reg.append(self._get_voucher_type(cr, uid, invoice))
            # 'controlador'
            type1_reg.append(' ')
            # 'punto_venta'
            type1_reg.append(invoice.pos_ar_id.name)
            # 'numero_comprobante'
            type1_reg.append(invoice.internal_number)
            # 'numero_comprobante_reg'
            type1_reg.append(invoice.internal_number)
            # 'cantidad_hojas'
            type1_reg.append('001')
            # 'codigo_doc_ident_comprador'
            type1_reg.append(code)
            # 'numero_ident_comprador'
            type1_reg.append(number)
            # 'apenom_comprador'
            type1_reg.append(self._get_partner_name(invoice))
            # 'importe_total'
            type1_reg.append(moneyfmt(Decimal(str(importe_total)), places=2, ndigits=15, dp='', sep=''))
            # 'neto_no_gravado'
            type1_reg.append(moneyfmt(Decimal(str(importe_neto_no_gravado)), places=2, ndigits=15, dp='', sep=''))
            # 'neto_gravado'
            type1_reg.append(moneyfmt(Decimal(str(importe_neto)), places=2, ndigits=15, dp='', sep=''))
            # 'impuesto_liquidado'
            type1_reg.append(moneyfmt(Decimal(str(importe_iva)), places=2, ndigits=15, dp='', sep=''))
            # 'impuesto_rni'
            type1_reg.append(moneyfmt(Decimal('0.0'), places=2, ndigits=15, dp='', sep=''))
            # 'impuesto_op_exentas'
            type1_reg.append(moneyfmt(Decimal(str(importe_operaciones_exentas)), places=2, ndigits=15, dp='', sep=''))
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
            type1_reg.append(len(iva_array) and str(len(iva_array)) or '1')
            # 'codigo_operacion'
            type1_reg.append(self._get_operation_code(cr,uid, importe_iva, importe_neto_no_gravado, invoice))
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
                print r
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
        "JOIN res_partner par on par.id=i.partner_id, electronic_invoice_voucher_type evt " \
        "WHERE p.id=%(period)s AND evt.denomination_id=i.denomination_id " \
        "AND i.state in %(state)s AND evt.document_type=i.type " \
        "ORDER BY i.date_invoice, evt.code, pos.name, i.internal_number "

        cr.execute(invoice_query, {'period': period.id, 'state': ('open', 'paid',)})
        res = cr.fetchall()
        invoice_ids = [ids[0] for ids in res]

        period_split = period.code.split('/')
        period_name = period_split[1]+period_split[0]

        # Generamos los registros de Cabecera Tipo 1 y Tipo 2
        self._generate_head_file(cr, uid, company, period.id, period_name, invoice_ids, context)

        # Generamos los registros de Detalle Tipo 1
        self._generate_detail_file(cr, uid, company, period.id, period_name, invoice_ids, context)

        # Generamos los registros de Ventas Tipo 1 y Tipo 2
        #self._generate_sales_file(cr, uid, company, period_name, invoice_ids, context)

        return {'type': 'ir.actions.act_window_close'}

create_sired_files()
