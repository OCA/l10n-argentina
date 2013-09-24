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

from ..fixed_width import FixedWidth
from ..fixed_width import moneyfmt
from fixed_width_dicts import HEAD_LINES, HEAD_TYPE2_LINES, DETAIL_LINES, SALE_LINES, SALE_TYPE2_LINES, PURCHASE_LINES, PURCHASE_TYPE2_LINES
    
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
        if int(invoice.fiscal_position.afip_code) == 5 and invoice.amount_total <= 1000.0:
            return 'CONSUMIDOR FINAL'

        return invoice.partner_id.name

    def _get_invoice_vat_taxes(self, cr, uid, invoice, context=None):

        iva_array = []
        taxes = invoice.tax_line

        for tax in taxes:
            iva2 = {}
            if tax.tax_id.tax_group == 'vat':
                if tax.is_exempt:
                    iva2 = {'IVA': 0, 'type': 'vat', 'BaseImp': 0, 'Importe': 0}
                else:
                    percent_amount = tax.tax_id.amount
                    iva2 = {'IVA': percent_amount, 'type': 'vat', 'BaseImp': tax.base, 'Importe': tax.amount}
            elif tax.tax_id.tax_group == 'internal':
                iva2 = {'IVA': 0, 'type': 'internal', 'BaseImp': tax.base, 'Importe': tax.amount}
            else:
                continue

            iva_array.append(iva2)

        if len(iva_array) == 0:
            iva_array.append({'IVA': 0, 'type': 'vat', 'BaseImp': 0, 'Importe': 0})

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
        if partner.document_type_id.afip_code == '99' or not partner.document_type_id:
            if invoice.amount_total <= 1000:
                return '99', '0'*11
            else:
                raise osv.except_osv(_('SIRED Error!'), _('Cannot inform invoice %s%s because amount total is greater than 1000 and partner (%s) has not got document identification') % (invoice.denomination_id.name, invoice.internal_number, invoice.partner_id.name))

        code = partner.document_type_id and partner.document_type_id.afip_code or False
        if not code or not partner.vat:
            raise osv.except_osv(_('SIRED import Error!'), _('Cannot inform invoice %s%s because partner (%s) has not got document identification') % (invoice.denomination_id.name, invoice.internal_number, invoice.partner_id.name))

        return code, partner.vat

    # Usa HEAD_LINES Y HEAD_TYPE2_LINES
    def _generate_head_file(self, cr, uid, company, period_id, period_name, invoice_ids, context):
        invoice_obj = self.pool.get('account.invoice')
        voucher_type_obj = self.pool.get('wsfe.voucher_type')

        importe_total_reg1 = 0.0
        importe_total_neto_no_gravado_reg1 = 0.0
        importe_total_neto_reg1 = 0.0
        importe_total_iva_reg1 = 0.0
        importe_total_operaciones_exentas_reg1 = 0.0

        head_regs = []
        fixed_width = FixedWidth(HEAD_LINES)
        
        for invoice in invoice_obj.browse(cr, uid, invoice_ids, context):
            
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
            voucher_type = voucher_type_obj.get_voucher_type(cr, uid, invoice, context=context)

            iva_array = self._get_invoice_vat_taxes(cr, uid, invoice, context)

            line = {
                'type': 1,
                'date_invoice': date_invoice,
                'voucher_type': voucher_type,
                'fiscal_controller': ' ',
                'pos_ar': pos_ar,
                'invoice_number': invoice_number,
                'invoice_number_reg': invoice_number,
                'cant_hojas': '001',
                'code': code,
                'number': number,
                'partner_name': self._get_partner_name(invoice),
                'total': moneyfmt(Decimal(invoice.amount_total), places=2, ndigits=15),
                'neto_no_gravado': moneyfmt(Decimal(invoice.amount_no_taxed), places=2, ndigits=15),
                'neto_gravado': moneyfmt(Decimal(invoice.amount_taxed), places=2, ndigits=15),
                'impuesto_liquidado': moneyfmt(Decimal(invoice.amount_tax), places=2, ndigits=15),
                'impuesto_rni': moneyfmt(Decimal(0.0)),
                'impuesto_op_exentas': moneyfmt(Decimal(invoice.amount_exempt), places=2, ndigits=15),
                'percep_imp_nacionales': moneyfmt(Decimal(0.0)),
                'percep_iibb': moneyfmt(Decimal(0.0)),
                'percep_municipales': moneyfmt(Decimal(0.0)),
                'impuestos_internos': moneyfmt(Decimal(0.0)),
                'transporte': moneyfmt(Decimal(0.0)),
                'tipo_responsable': invoice.fiscal_position.afip_code,
                'codigo_moneda': invoice.currency_id.afip_code,
                'tipo_cambio': moneyfmt(Decimal(1.0), places=6, ndigits=10),
                'cant_alicuotas_iva': str(len(iva_array)),
                'codigo_operacion': self._get_operation_code(cr,uid, invoice),
                'cae': invoice.cae,
                'fecha_vencimiento': cae_due_date,
                'fecha_anulacion': ''
            }

            # Apendeamos el registro
            fixed_width.update(**line)
            head_regs.append(fixed_width.line)

        # Creacion del registro tipo 2 (Totales)
        company_cuit = company.partner_id.vat
        
        fixed_width = FixedWidth(HEAD_TYPE2_LINES)
        
        type2_reg = {
            'period': period_name,
            'amount': len(head_regs),
            'company_cuit': company_cuit,
            'total': moneyfmt(Decimal(importe_total_reg1), places=2, ndigits=15),
            'neto_no_gravado': moneyfmt(Decimal(importe_total_neto_no_gravado_reg1), places=2, ndigits=15),
            'neto_gravado': moneyfmt(Decimal(importe_total_neto_reg1), places=2, ndigits=15),
            'impuesto_liquidado': moneyfmt(Decimal(importe_total_iva_reg1), places=2, ndigits=15),
            'impuesto_rni': moneyfmt(Decimal(0.0)),
            'impuesto_op_exentas': moneyfmt(Decimal(importe_total_operaciones_exentas_reg1), places=2, ndigits=15),
            'percep_imp_nacionales': moneyfmt(Decimal(0.0)),
            'percep_iibb': moneyfmt(Decimal(0.0)),
            'percep_municipales': moneyfmt(Decimal(0.0)),
            'impuestos_internos': moneyfmt(Decimal(0.0))
        }
        
        fixed_width.update(**type2_reg)
        head_regs.append(fixed_width.line)

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
            'datas_fname': name,
            'res_model': 'account.period',
            'res_id': period_id,
        }
        self.pool.get('ir.attachment').create(cr, uid, data_attach, context=context)
        f.close()

        return head_regs

    def _get_vat_tax_and_exempt_indicator(self, cr, uid, line_taxes):
        wsfe_conf_obj = self.pool.get('wsfe.config')
        conf = wsfe_conf_obj.get_config(cr, uid)

        # Tomamos la primer tax que encontremos en la configuracion
        # Evidentemente AFIP solo espera un IVA por linea por eso apenas
        # encontramos una que tenga codificacion, retornamos
        # TODO: Mejorar toda esta parte de impuestos de AFIP
        for tax in line_taxes:
            for eitax in conf.vat_tax_ids+conf.exempt_operations_tax_ids:
                if eitax.tax_code_id.id == tax.tax_code_id.id:
                    if eitax.exempt_operations:
                        return '0', 'E'
                    else:
                        return tax.amount*100, 'G'

        # Si es No Gravado
        return '0', 'N'

    # Usa DETAIL_LINES
    def _generate_detail_file(self, cr, uid, company, period_id, period_name, invoice_ids, context):
        invoice_obj = self.pool.get('account.invoice')
        voucher_type_obj = self.pool.get('wsfe.voucher_type')

        detail_regs = []
        fixed_width = FixedWidth(DETAIL_LINES)
        
        for invoice in invoice_obj.browse(cr, uid, invoice_ids, context):
            # Conversiones varias
            date_val = time.strptime(invoice.date_invoice, '%Y-%m-%d')
            date_invoice = time.strftime('%Y%m%d', date_val) # AAAAMMDD

            pos_ar, invoice_number = invoice.internal_number.split('-')
            voucher_type = voucher_type_obj.get_voucher_type(cr, uid, invoice, context=context)

            for line in invoice.invoice_line:

                if not line.uos_id.afip_code:
                    raise osv.except_osv(_('SIRED Error!'), _('You have to configure AFIP Code for UoM %s') % (line.uos_id.name))

                iva, exempt_indicator = self._get_vat_tax_and_exempt_indicator(cr, uid, line.invoice_line_tax_id)

                detail_line = {
                    'voucher_type': voucher_type,
                    'date_invoice': date_invoice,
                    'pos_ar': pos_ar,
                    'invoice_number': invoice_number,
                    'invoice_number_reg': invoice_number,
                    'quantity': moneyfmt(Decimal(line.quantity), places=5, ndigits=12),
                    'uom': line.uos_id.afip_code,
                    'price_unit': moneyfmt(Decimal(line.price_unit), places=3, ndigits=16),
                    #TODO: Tener en cuenta los descuentos
                    'bonus_amount': moneyfmt(Decimal(0.0), places=2, ndigits=15),
                    'adjustment_amount': moneyfmt(Decimal(0.0), places=3, ndigits=16),
                    'subtotal': moneyfmt(Decimal(line.price_subtotal), places=3, ndigits=16),
                    'iva': moneyfmt(Decimal(iva), places=2, ndigits=4),
                    'exempt_indicator': exempt_indicator,
                    'product_name': line.name
                }

                # Apendeamos el registro
                fixed_width.update(**detail_line)
                detail_regs.append(fixed_width.line)

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
            'datas_fname': name,
            'res_model': 'account.period',
            'res_id': period_id,
        }
        self.pool.get('ir.attachment').create(cr, uid, data_attach, context=context)
        f.close()

        return detail_regs

    # Usa SALE_LINES y SALE_TYPE2_LINES
    def _generate_sales_file(self, cr, uid, company, period_id, period_name, invoice_ids, context):
        invoice_obj = self.pool.get('account.invoice')
        voucher_type_obj = self.pool.get('wsfe.voucher_type')

        importe_total_reg1 = 0.0
        importe_total_neto_no_gravado_reg1 = 0.0
        importe_total_neto_reg1 = 0.0
        importe_total_iva_reg1 = 0.0
        importe_total_operaciones_exentas_reg1 = 0.0

        # Totales de Percepciones
        # TODO: Implementar Percepciones en VENTAS
        #percepciones_iva_reg1 = 0.0
        #percepciones_nacionales_reg1 = 0.0
        #percepciones_iibb_reg1 = 0.0
        #percepciones_municipales_reg1 = 0.0

        sale_regs = []
        fixed_width = FixedWidth(SALE_LINES)

        for invoice in invoice_obj.browse(cr, uid, invoice_ids, context):

            # Conversiones varias
            date_val = time.strptime(invoice.date_invoice, '%Y-%m-%d')
            date_invoice = time.strftime('%Y%m%d', date_val) # AAAAMMDD

            cae_due_date_val = time.strptime(invoice.cae_due_date, '%Y-%m-%d')
            cae_due_date = time.strftime('%Y%m%d', cae_due_date_val) # AAAAMMDD

            code, number = self._get_identifier_document_code_and_number(cr, uid, invoice)

            # Importe total de todos los registros 1
            importe_total_reg1 += invoice.amount_total
            importe_total_neto_no_gravado_reg1 += invoice.amount_no_taxed
            importe_total_neto_reg1 += invoice.amount_taxed
            importe_total_iva_reg1 += invoice.amount_tax
            importe_total_operaciones_exentas_reg1 += invoice.amount_exempt

            pos_ar, invoice_number = invoice.internal_number.split('-')
            voucher_type = voucher_type_obj.get_voucher_type(cr, uid, invoice, context=context)

            iva_array = self._get_invoice_vat_taxes(cr, uid, invoice, context)


            for alic_iva in iva_array:

                line = {
                    'type': 1,
                    'date_invoice': date_invoice,
                    'voucher_type': voucher_type,
                    'pos_ar': pos_ar,
                    'invoice_number': invoice_number,
                    'invoice_number_reg': invoice_number,
                    'code': code,
                    'number': number,
                    'partner_name': self._get_partner_name(invoice),
                    'total': moneyfmt(Decimal(0.0)),
                    'neto_no_gravado': moneyfmt(Decimal(invoice.amount_no_taxed), places=2, ndigits=15),
                    'neto_gravado': moneyfmt(Decimal(alic_iva['BaseImp']), places=2, ndigits=15),
                    'alic_iva': int(alic_iva['IVA']*10000),
                    'impuesto_liquidado': moneyfmt(Decimal(alic_iva['Importe']), places=2, ndigits=15),
                    'impuesto_rni': moneyfmt(Decimal(0.0)),
                    'impuesto_op_exentas': moneyfmt(Decimal(invoice.amount_exempt), places=2, ndigits=15),
                    'percep_imp_nacionales': moneyfmt(Decimal(0.0)),
                    'percep_iibb': moneyfmt(Decimal(0.0)),
                    'percep_municipales': moneyfmt(Decimal(0.0)),
                    'impuestos_internos': moneyfmt(Decimal(0.0)),
                    'tipo_responsable': invoice.fiscal_position.afip_code,
                    'codigo_moneda': invoice.currency_id.afip_code,
                    'tipo_cambio': moneyfmt(Decimal(1.0), places=6, ndigits=10),
                    'cant_alicuotas_iva': len(iva_array) and str(len(iva_array)) or '1',
                    'codigo_operacion': self._get_operation_code(cr, uid, invoice),
                    'cae': invoice.cae,
                    'fecha_vencimiento': cae_due_date,
                    'fecha_anulacion': ''
                }

                # Apendeamos el registro
                fixed_width.update(**line)
                sale_regs.append(fixed_width.line)

            # En el ultimo reg1 consignamos valores totales segun la RG            
            line['total'] = moneyfmt(Decimal(invoice.amount_total), places=2, ndigits=15)
            
            fixed_width.update(**line)
            sale_regs[-1] = fixed_width.line

        # Creacion del registro tipo 2 (Totales)
        company_cuit = company.partner_id.vat

        fixed_width = FixedWidth(SALE_TYPE2_LINES)
        
        type2_reg = {
            'period': period_name,
            'amount': len(sale_regs),
            'company_cuit': company_cuit,
            'total': moneyfmt(Decimal(importe_total_reg1), places=2, ndigits=15),
            'neto_no_gravado': moneyfmt(Decimal(importe_total_neto_no_gravado_reg1), places=2, ndigits=15),
            'neto_gravado': moneyfmt(Decimal(importe_total_neto_reg1), places=2, ndigits=15),
            'impuesto_liquidado': moneyfmt(Decimal(importe_total_iva_reg1), places=2, ndigits=15),
            'impuesto_rni': moneyfmt(Decimal(0.0)),
            'impuesto_op_exentas': moneyfmt(Decimal(importe_total_operaciones_exentas_reg1), places=2, ndigits=15),
            'percep_imp_nacionales': moneyfmt(Decimal(0.0)),
            'percep_iibb': moneyfmt(Decimal(0.0)),
            'percep_municipales': moneyfmt(Decimal(0.0)),
            'impuestos_internos': moneyfmt(Decimal(0.0))
        }
        
        fixed_width.update(**type2_reg)
        sale_regs.append(fixed_width.line)

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
            'datas_fname': name,
            'res_model': 'account.period',
            'res_id': period_id,
        }
        self.pool.get('ir.attachment').create(cr, uid, data_attach, context=context)
        f.close()

        return sale_regs

    def _generate_purchase_file(self, cr, uid, company, period_id, period_name, invoice_ids, context):
        invoice_obj = self.pool.get('account.invoice')

        importe_total_reg1 = 0.0
        importe_total_neto_no_gravado_reg1 = 0.0
        importe_total_neto_reg1 = 0.0
        importe_total_iva_reg1 = 0.0
        importe_total_operaciones_exentas_reg1 = 0.0

        impuestos_internos_reg1 = 0.0

        # Totales de Percepciones
        percepciones_iva_reg1 = 0.0
        percepciones_nacionales_reg1 = 0.0
        percepciones_iibb_reg1 = 0.0
        percepciones_municipales_reg1 = 0.0

        purchase_regs = []
        fixed_width = FixedWidth(PURCHASE_LINES)

        for invoice in invoice_obj.browse(cr, uid, invoice_ids, context):

            impuestos_internos = 0.0

            # Conversiones varias
            date_val = time.strptime(invoice.date_invoice, '%Y-%m-%d')
            date_invoice = time.strftime('%Y%m%d', date_val) # AAAAMMDD

            cae_due_date = '2013-01-01'
            #cae_due_date_val = time.strptime(invoice.cae_due_date, '%Y-%m-%d')
            #cae_due_date = time.strftime('%Y%m%d', cae_due_date_val) # AAAAMMDD

            code, number = self._get_identifier_document_code_and_number(cr, uid, invoice)

            # Importe total de todos los registros 1
            importe_total_reg1 += invoice.amount_total
            importe_total_neto_no_gravado_reg1 += invoice.amount_no_taxed
            importe_total_neto_reg1 += invoice.amount_taxed
            importe_total_iva_reg1 += invoice.amount_tax
            importe_total_operaciones_exentas_reg1 += invoice.amount_exempt

            pos_ar, invoice_number = invoice.internal_number.split('-')
            #tipo_cbte = voucher_type_obj.get_voucher_type(cr, uid, invoice, context=context)

            # TODO: Cambiar este HARDCODED
            tipo_cbte = None
            if invoice.type == 'in_invoice':
                if not invoice.is_debit_note:
                    if invoice.denomination_id.name=='A':
                        tipo_cbte = '01'
                    elif invoice.denomination_id.name == 'B':
                        tipo_cbte = '06'
                    elif invoice.denomination_id.name == 'C':
                        tipo_cbte = '11'
                # Notas de Debito
                else:
                    if invoice.denomination_id.name=='A':
                        tipo_cbte = '02'
                    elif invoice.denomination_id.name == 'B':
                        tipo_cbte = '07'
                    elif invoice.denomination_id.name == 'C':
                        tipo_cbte = '12'
            elif invoice.type == 'in_refund':
                if invoice.denomination_id.name=='A':
                    tipo_cbte = '03'
                elif invoice.denomination_id.name == 'B':
                    tipo_cbte = '08'
                elif invoice.denomination_id.name == 'C':
                    tipo_cbte = '13'

            if not tipo_cbte:
                raise osv.except_osv(_('SIRED Error'), _('Cannot be determined the type of voucher [%s]') % (invoice.internal_number))

            iva_array = self._get_invoice_vat_taxes(cr, uid, invoice, context)

            for alic_iva in iva_array:

                if alic_iva['type'] == 'internal':
                    impuestos_internos += alic_iva['Importe']
                    continue
            
                line = {
                    'type': 1,
                    'date_invoice': date_invoice,
                    'voucher_type': tipo_cbte,
                    'pos_ar': pos_ar,
                    'invoice_number': invoice_number,
                    'date_invoice2': date_invoice,
                    'codigo_aduana': '000',
                    'codigo_destinacion': ' ',
                    'verificador_numero_despacho': ' ',
                    'code': code,
                    'number': number,
                    'partner_name': self._get_partner_name(invoice),
                    'total': moneyfmt(Decimal(0.0)),
                    'neto_no_gravado': moneyfmt(Decimal(invoice.amount_no_taxed), places=2, ndigits=15),
                    'neto_gravado': moneyfmt(Decimal(alic_iva['BaseImp']), places=2, ndigits=15),
                    'alic_iva': int(alic_iva['IVA']*10000),
                    'impuesto_liquidado': moneyfmt(Decimal(alic_iva['Importe']), places=2, ndigits=15),
                    'impuesto_rni': moneyfmt(Decimal(0.0), places=2, ndigits=15),
                    'impuesto_op_exentas': moneyfmt(Decimal(invoice.amount_exempt), places=2, ndigits=15),
                    'percep_iva': moneyfmt(Decimal(0.0)),
                    'percep_imp_nacionales': moneyfmt(Decimal(0.0)),
                    'percep_iibb': moneyfmt(Decimal(0.0)),
                    'percep_municipales': moneyfmt(Decimal(0.0)),
                    'impuestos_internos': moneyfmt(Decimal(0.0)),
                    'tipo_responsable': invoice.fiscal_position.afip_code,
                    'codigo_moneda': invoice.currency_id.afip_code,
                    'tipo_cambio': moneyfmt(Decimal(1.0), places=6, ndigits=10),
                    'cant_alicuotas_iva': len(iva_array) and str(len(iva_array)) or '1',
                    'codigo_operacion': self._get_operation_code(cr, uid, invoice),
                    'cae': invoice.cae or '000000000000',
                    'fecha_vencimiento': cae_due_date
                }

                # Apendeamos el registro
                fixed_width.update(**line)
                purchase_regs.append(fixed_width.line)

            # Obtenemos los importes de percepciones
            percepciones_iva = 0.0
            percepciones_iibb = 0.0
            percepciones_nacionales = 0.0
            percepciones_municipales = 0.0

            for perc in invoice.perception_ids:
                if perc.perception_id.type == 'vat':
                    percepciones_iva += perc.amount
                elif perc.perception_id.type == 'gross_income':
                    percepciones_iibb += perc.amount
                elif perc.perception_id.jurisdiccion == 'nacional':
                    percepciones_nacionales += perc.amount
                elif perc.perception_id.jurisdiccion == 'municipal':
                    percepciones_municipales += perc.amount

            # En el ultimo registro consignamos valores totales segun la RG
            line['total'] = moneyfmt(Decimal(invoice.amount_total), places=2, ndigits=15)
            line['percep_iva'] = moneyfmt(Decimal(percepciones_iva), places=2, ndigits=15)
            line['percep_imp_nacionales'] = moneyfmt(Decimal(percepciones_nacionales), places=2, ndigits=15)
            line['percep_iibb'] = moneyfmt(Decimal(percepciones_iibb), places=2, ndigits=15)
            line['percep_municipales'] = moneyfmt(Decimal(percepciones_municipales), places=2, ndigits=15)
            line['impuestos_internos'] = moneyfmt(Decimal(impuestos_internos), places=2, ndigits=15)

            percepciones_iva_reg1 += percepciones_iva
            percepciones_nacionales_reg1 += percepciones_nacionales
            percepciones_iibb_reg1 += percepciones_iibb
            percepciones_municipales_reg1 += percepciones_municipales
            impuestos_internos_reg1 += impuestos_internos
            
            fixed_width.update(**line)
            purchase_regs[-1] = fixed_width.line

        # Creacion del registro tipo 2 (Totales)
        company_cuit = company.partner_id.vat

        fixed_width = FixedWidth(PURCHASE_TYPE2_LINES)
        
        type2_reg = {
            'period': period_name,
            'amount': len(purchase_regs),
            'company_cuit': company_cuit,
            'total': moneyfmt(Decimal(importe_total_reg1), places=2, ndigits=15),
            'neto_no_gravado': moneyfmt(Decimal(importe_total_neto_no_gravado_reg1), places=2, ndigits=15),
            'neto_gravado': moneyfmt(Decimal(importe_total_neto_reg1), places=2, ndigits=15),
            'impuesto_liquidado': moneyfmt(Decimal(importe_total_iva_reg1), places=2, ndigits=15),
            'importe_op_exentas': moneyfmt(Decimal(importe_total_operaciones_exentas_reg1), places=2, ndigits=15),
            'percep_iva': moneyfmt(Decimal(percepciones_iva_reg1), places=2, ndigits=15),
            'percep_imp_nacionales': moneyfmt(Decimal(percepciones_nacionales_reg1), places=2, ndigits=15),
            'percep_iibb': moneyfmt(Decimal(percepciones_iibb_reg1), places=2, ndigits=15),
            'percep_municipales': moneyfmt(Decimal(percepciones_municipales_reg1), places=2, ndigits=15),
            'impuestos_internos': moneyfmt(Decimal(impuestos_internos_reg1), places=2, ndigits=15),
        }
        
        fixed_width.update(**type2_reg)
        purchase_regs.append(fixed_width.line)

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
            'datas_fname': name,
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
        # TODO: Implementar impuestos_internos
        self._generate_head_file(cr, uid, company, period.id, period_name, invoice_ids, context)

        # Generamos los registros de Detalle Tipo 1
        # TODO: Implementar impuestos_internos
        self._generate_detail_file(cr, uid, company, period.id, period_name, invoice_ids, context)

        # Generamos los registros de Ventas Tipo 1 y Tipo 2
        # TODO: Implementar impuestos_internos
        self._generate_sales_file(cr, uid, company, period.id, period_name, invoice_ids, context)

        # Generamos los registros de Compras Tipo 1 y Tipo 2
        purchase_invoice_query = "SELECT i.id " \
        "FROM account_invoice i " \
        "JOIN account_period p on p.id=i.period_id " \
        "JOIN invoice_denomination d on d.id=i.denomination_id " \
        "JOIN res_partner par on par.id=i.partner_id " \
        "WHERE p.id=%(period)s " \
        "AND i.state in %(state)s " \
        "AND i.type in %(invoice_types)s " \
        "ORDER BY i.date_invoice, i.internal_number "

        cr.execute(purchase_invoice_query, {'period': period.id, 'state': ('open', 'paid',), 'invoice_types': ('in_invoice', 'in_refund',)})
        res = cr.fetchall()
        invoice_ids = [ids[0] for ids in res]

        # Generamos los registros de Compras
        self._generate_purchase_file(cr, uid, company, period.id, period_name, invoice_ids, context)

        return {'type': 'ir.actions.act_window_close'}

create_sired_files()
