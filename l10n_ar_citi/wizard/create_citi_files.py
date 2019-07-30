##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

import time
import re
import logging
from decimal import Decimal

from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF

from odoo.addons.base_report_exporter.utils.fixed_width import moneyfmt
from .fixed_width_dicts import ALIQOUT_PURCHASES, ALIQOUT_SALES, \
    PURCHASES_VOUCHER, SALES_VOUCHER  # , TODO IMPORTATION_PURCHASES

_logger = logging.getLogger(__name__)

re_import_delivery = re.compile('\d{2}\d{3}[A-Z]{2}\d{2}\d{6}[A-Z]')
settlements_voucher_types = {'033', '058', '059', '060', '063'}
class_a = {1, 2, 3, 4, 5, 17, 60, 63, 81, 112, 115}  # Class A
class_c = {11, 12, 13, 15, 16, 36, 41, 111, 114, 117}  # Class C
class_m = {51, 52, 53, 54, 55, 56, 57, 58, 59, 118, 119, 121}  # Class M
class_a_c_and_m_voucher_types = set().union(class_a, class_c, class_m)
other_vouchers_types = {90, 99}
amount_name_map = {
    "amount_total": "Total",
    "amount_net": "Base",
    "amount_tax": "de Impuesto Liquidado",
    "amount_total_non_net": "No gravado",
    "amount_non_categ_perception": "de Percepcion a No Categorizados",
    "amount_exempt_transactions": "Exento",
    "amount_perceptions_or_vat_national_taxes": "de Percepciones de IVA",
    "amount_perceptions_national_taxes": "de Percepciones Nacionales",
    "amount_gross_income_perceptions": "de Percepciones de Ingresos Brutos",
    "amount_perceptions_city_taxes": "de Percepciones Municipales",
    "amount_resident_taxes": "de Impuestos Internos",
}


def _fmt(amount, places=2, ndigits=15):
    return moneyfmt(Decimal(amount), places=places, ndigits=ndigits)


def _any_error(errors):
    return any(
        map(
            lambda err: err.get('type', 'error') == 'error',
            errors
        )
    )


class CreateCitiFiles(models.TransientModel):
    _name = 'create.citi.files'
    _desc = 'Create CITI Files'

    period_id = fields.Many2one('date.period', 'Period')
    notes = fields.Text('Notes', readonly=True)
    state = fields.Selection([
        ('init', 'Start'),
        ('done', 'Done')], 'State',
        default='init')


class ReportFilesGenerator(models.Model):
    _inherit = 'report.files.generator'

    @api.multi
    def _do_citi(self):
        """
        Must return the exact format:
        ddict = {
            'state': True|False, # report status
            'errors': [{'resource': recordset, 'error': 'error'}]
            # recordset ensured one
            'files': [{'name': 'filename', 'data': IO Buffer}]
        }
        """
        res = {
            'state': True,
            'files': [],
            'errors': [],
        }
        sales_data = self._create_sales_files()
        purchases_data = self._create_purchases_files()
        res['files'] += sales_data.get('files', []) + \
            purchases_data.get('files', [])
        res['errors'] += sales_data.get('errors', []) + \
            purchases_data.get('errors', [])
        if _any_error(res['errors']):
            res['state'] = False
        if not res['errors'] and not res['files']:
            return False
        return res

    @api.multi
    def _create_sales_files(self):
        invoices = self._get_invoice_recordset(
            invoice_types=tuple(['out_invoice', 'out_refund']),
        )
        voucher_data = []
        aliquot_data = []
        errors = []
        resulting_files = []
        for invoice in invoices:
            voucher_parsed_line, aliquot_parsed_line, inv_errors = \
                self._generate_sale_lines_from_invoice(invoice)
            voucher_data += voucher_parsed_line
            aliquot_data += aliquot_parsed_line
            errors += inv_errors
        if voucher_data:
            voucher_file = {
                'name': 'REGINFO_CV_VENTAS_CBTE.txt',
                'data': voucher_data,
            }
            resulting_files.append(voucher_file)
        if aliquot_data:
            aliquot_file = {
                'name': 'REGINFO_CV_VENTAS_ALICUOTAS.txt',
                'data': aliquot_data,
            }
            resulting_files.append(aliquot_file)
        result = {
            'files': resulting_files,
            'errors': errors,
        }
        return result

    @api.multi
    def _create_purchases_files(self):
        invoices = self._get_invoice_recordset(
            invoice_types=tuple(['in_invoice', 'in_refund']),
        )
        voucher_data = []
        aliquot_data = []
        import_data = []
        errors = []
        resulting_files = []
        for invoice in invoices:
            voucher_parsed_line, aliquot_parsed_line, \
                import_parsed_line, inv_errors = \
                self._generate_purchase_lines_from_invoice(invoice)
            voucher_data += voucher_parsed_line
            aliquot_data += aliquot_parsed_line
            import_data += import_parsed_line
            errors += inv_errors
        if voucher_data:
            voucher_file = {
                'name': 'REGINFO_CV_COMPRAS_CBTE.txt',
                'data': voucher_data,
            }
            resulting_files.append(voucher_file)
        if aliquot_data:
            aliquot_file = {
                'name': 'REGINFO_CV_COMPRAS_ALICUOTAS.txt',
                'data': aliquot_data,
            }
            resulting_files.append(aliquot_file)
        if import_data:
            import_file = {
                'name': 'REGINFO_CV_COMPRAS_IMPORTACIONES.txt',
                'data': import_data,
            }
            resulting_files.append(import_file)
        result = {
            'files': resulting_files,
            'errors': errors,
        }
        return result

    @api.model
    def _get_general_fields(self, invoice):
        errors = []
        partner = invoice.partner_id

        # Date Voucher
        date_val = time.strptime(invoice.date_invoice, DSDF)
        date_voucher = time.strftime('%Y%m%d', date_val)  # AAAAMMDD

        # Voucher Type
        try:
            voucher_type = invoice._get_voucher_type()
        except Exception:
            voucher_type = '000'
            errors.append({
                'resource': invoice,
                'error': (_("Could not find a proper voucher type " +
                            "for invoice %s") %
                          (invoice.name_get()[0][1])),
            })

        # PoS & Voucher ID
        pos, voucher_id = invoice.split_number()
        max_voucher_id = voucher_id

        # Document Type
        document_type = partner.document_type_id and \
            int(partner.document_type_id.afip_code) or 99

        # Partner ID
        partner_id = (partner.vat or '0') if document_type != '99' \
            else '9' * 11

        # Partner Name
        partner_name = self._get_partner_name(invoice)

        # Vat Aliquot Qty
        if int(voucher_type) in class_c:
            taxes_info = {
                'taxes': {},
                'aliquot_qty': 0,
                'amount_net_aditional': 0,
                'computed_fiscal_credit': 0,
                'transaction_code': ' ',
                'errors': [],
            }
        else:
            taxes_info = self._get_taxes_info(invoice)
        errors += taxes_info.get('errors', [])
        vat_aliquot_qty = taxes_info.get('aliquot_qty')
        comp_fc = _fmt(taxes_info.get('computed_fiscal_credit'))

        # Amounts
        _amount_net_aditional = taxes_info.get('amount_net_aditional')
        amount_total = _fmt(invoice.amount_total + _amount_net_aditional)
        amount_total_non_net = _fmt(invoice.amount_no_taxed)
        amount_non_categ_perception = moneyfmt(Decimal(0.0))
        amount_exempt_transactions = _fmt(invoice.amount_exempt)
        amount_perceptions_national_taxes, amount_gross_income_perceptions, \
            amount_perceptions_city_taxes, \
            amount_perceptions_or_vat_national_taxes = \
            self._get_perceptions_amount(invoice)
        amount_resident_taxes = moneyfmt(Decimal(0.0))

        # TODO Also in class_b [Define]
        if int(voucher_type) in class_c:
            amount_total_non_net = _fmt(0.0)
            amount_exempt_transactions = _fmt(0.0)
            amount_perceptions_national_taxes, \
                amount_gross_income_perceptions, \
                amount_perceptions_city_taxes, \
                amount_perceptions_or_vat_national_taxes = \
                [_fmt(0.0)] * 4

        # Currency Code
        currency_code = invoice.currency_id.afip_code

        # Change Type
        # TODO Multicurrency
        change_type = moneyfmt(Decimal(1.0), places=6, ndigits=10)

        # Transaction Code
        transaction_code = taxes_info.get('transaction_code')

        # Others
        others = moneyfmt(Decimal(0.0))

        # Date Payment Due
        date_payment_due = 0

        return locals().copy()

    @api.model
    def _generate_sale_lines_from_invoice(self, invoice):
        data = self._get_general_fields(invoice)
        errors = data.get('errors', [])

        taxes_info = data.get('taxes_info')
        vat_aliquot_qty = data.get('vat_aliquot_qty')

        errors += self._process_sale_line_errors(invoice, data)

        aliquot_data = []

        taxes = taxes_info.get('taxes', {})
        for vat_aliquot, tax_data in taxes.items():
            amount_net = _fmt(tax_data.get('base'))
            amount_tax = _fmt(tax_data.get('amount'))
            data.update(locals().copy())
            aliquot_parsed_line = self._parsed_line_from_locals(
                data, ALIQOUT_SALES)
            aliquot_data.append(aliquot_parsed_line)

        voucher_parsed_line = self._parsed_line_from_locals(
            data, SALES_VOUCHER)
        voucher_data = [voucher_parsed_line]

        return (voucher_data, aliquot_data, errors)

    @api.model
    def _generate_purchase_lines_from_invoice(self, invoice):
        data = self._get_general_fields(invoice)
        errors = data.get('errors', [])

        seller_document_type = data.get('document_type')
        document_type_id = seller_document_type
        seller_id = data.get('partner_id')
        seller_name = data.get('partner_name')
        voucher_type = data.get('voucher_type')

        taxes_info = data.get('taxes_info')
        vat_aliquot_qty = data.get('vat_aliquot_qty')

        import_delivery = ''

        company = invoice.company_id
        cuit = 0
        partner_name = ''
        vat_assigment = 0
        if voucher_type in settlements_voucher_types:
            cuit = company.partner_id.vat
            partner_name = company.partner_id.name

        data.update(locals().copy())
        errors += self._process_purchase_line_errors(invoice, data)

        # TODO With Multicurrency
        import_data = []
        aliquot_data = []
        voucher_data = []
        if _any_error(errors):
            return (voucher_data, aliquot_data, import_data, errors)

        taxes = taxes_info.get('taxes', {})
        for vat_aliquot, tax_data in taxes.items():
            amount_net = _fmt(tax_data.get('base'))
            amount_tax = _fmt(tax_data.get('amount'))
            data.update(locals().copy())
            aliquot_parsed_line = self._parsed_line_from_locals(
                data, ALIQOUT_PURCHASES)
            aliquot_data.append(aliquot_parsed_line)

        voucher_parsed_line = self._parsed_line_from_locals(
            data, PURCHASES_VOUCHER)
        voucher_data = [voucher_parsed_line]

        return (voucher_data, aliquot_data, import_data, errors)

    @api.model
    def _process_purchase_line_errors(self, invoice, data):
        errors = []
        errors += self._process_generic_line_errors(invoice, data)
        return errors

    @api.model
    def _process_sale_line_errors(self, invoice, data):
        errors = []
        errors += self._process_generic_line_errors(invoice, data)
        return errors

    @api.model
    def _process_generic_line_errors(self, invoice, data):
        errors = []
        voucher_type = int(data.get('voucher_type'))
        document_type = data.get('document_type')
        pos = data.get('pos')
        _amount_net_aditional = data.get('_amount_net_aditional')
        # Campo codigo de documento debe ser igual a 80 para tipo de comprobante informado  # noqa
        if voucher_type in class_a_c_and_m_voucher_types and \
                document_type != 80:
            errors.append({
                'resource': invoice.partner_id,
                'error': (_("The document type of partner %s should be " +
                            "CUIT for invoice %s") %
                          (invoice.partner_id.name, invoice.name_get()[0][1])),
            })
        # El campo punto de venta no puede ser menor a 00001
        if voucher_type not in other_vouchers_types and \
                pos <= 0:
            errors.append({
                'resource': invoice,
                'error': (_("Point of sale can't be zero or lower for " +
                            "invoice %s\nYou can create an OC denomination " +
                            "and voucher type in order to use a not " +
                            "authorized point of sale.") %
                          (invoice.name_get()[0][1])),
            })
        # Montos negativos
        errors += [{
            'key': k,
            'type': 'warning',
            'resource': invoice,
            'error': (_("Amount %s can't be negative for invoice %s") %
                      (amount_name_map.get(k), invoice.name_get()[0][1])),
        } for k, v in data.items()
            if k.startswith('amount_') and
            not self._check_amount_negative(v)]
        for err in errors:
            data[err.get('key')] = _fmt(0)
        if _amount_net_aditional:
            errors.append({
                'type': 'warning',
                'resource': invoice,
                'error': (_("Tax base does not match total tax amount " +
                            "for invoice %s. Check out for tax lines not " +
                            "matching invoice line taxes") %
                          (invoice.name_get()[0][1])),
            })
        return errors

    @api.model
    def _check_amount_negative(self, amount):
        if isinstance(amount, str):
            if amount.find('-') != -1:
                return False
        else:
            try:
                return amount >= 0
            except Exception:
                return False
        return True

    @api.model
    def _parsed_line_from_locals(self, all_data, fixed_width_dict_obj):
        fields = [x for x in fixed_width_dict_obj.config.keys()]
        row_line = {k: v for k, v in all_data.items()
                    if k in fields}
        fixed_width_dict_obj.update(**row_line)
        return fixed_width_dict_obj.line

    @api.model
    def _get_taxes_info(self, invoice):
        errors = []
        vat_taxes = {}
        amount_net_aditional = 0.0
        computed_fiscal_credit = 0.0
        for tax_line in invoice.tax_line_ids:
            tax = tax_line.tax_id
            if tax.tax_group != 'vat':
                continue
            if not tax.amount and not tax.is_exempt:
                errors.append({
                    'resource': tax,
                    'error': (_("Tax percentage amount is configured as " +
                                "zero for tax %s. Used in invoice %s") %
                              (tax.name_get()[0][1],
                               invoice.name_get()[0][1])),
                })
                continue
            if not tax_line.amount and not tax.is_exempt:
                continue
            afip_code = tax.afip_code
            if not afip_code:
                errors.append({
                    'resource': tax,
                    'error': (_("Afip code is not set for tax %s used in " +
                                "invoice %s") %
                              (tax.name_get()[0][1],
                               invoice.name_get()[0][1])),
                })

            base = tax_line.base
            amount = tax_line.amount

            # Para calcular la base sobre las que se agregan manualmente
            if not base and tax_line.manual and not tax.is_exempt:
                base = amount * 100 / (tax.amount)
                amount_net_aditional += base

            vat_taxes.setdefault(afip_code, {
                'amount': 0.0,
                'base': 0.0,
            })
            if not tax.is_exempt:
                vat_taxes[afip_code]['amount'] += amount
                vat_taxes[afip_code]['base'] += base
            computed_fiscal_credit += amount

        if not invoice.tax_line_ids or not invoice.amount_total:
            # No taxed line is required if there are no taxes
            vat_taxes = {
                3: {
                    'base': 0.0,
                    'amount': 0.0,
                }
            }

        aliquot_qty = len(vat_taxes)

        """
        Z- Exportaciones a la zona franca.
        X- Exportaciones al Exterior.
        E- Operaciones Exentas.
        N- No Gravado

        Si tiene IVA se completará con espacios.
        """
        transaction_code = ' '
        if invoice.amount_exempt != 0:
            transaction_code = 'E'
        if invoice.amount_no_taxed != 0:
            transaction_code = 'N'

        res = {
            'taxes': vat_taxes,
            'aliquot_qty': aliquot_qty,
            'amount_net_aditional': amount_net_aditional,
            'computed_fiscal_credit': computed_fiscal_credit,
            'transaction_code': transaction_code,
            'errors': errors,
        }
        return res

    @api.model
    def _get_perceptions_amount(self, invoice):
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
        res = [
            moneyfmt(Decimal(abs(percepciones_nacionales))),
            moneyfmt(Decimal(abs(percepciones_iibb))),
            moneyfmt(Decimal(abs(percepciones_municipales))),
            moneyfmt(Decimal(abs(percepciones_iva))),
        ]
        return res

    @api.model
    def _get_partner_name(self, invoice):
        if int(invoice.fiscal_position_id.afip_code) == 5 and \
                invoice.amount_total < 5000:
            return 'CONSUMIDOR FINAL'
        elif int(invoice.fiscal_position_id.afip_code) == 99:
            return 'VENTA GLOBAL DIARIA'
        return invoice.partner_id.name

    @api.model
    def _get_invoice_recordset(self, **kwargs):
        query = """
        SELECT i.id
        FROM account_invoice i
        JOIN account_move m
            ON m.id = i.move_id
        JOIN date_period dp
            ON dp.id = m.period_id
        WHERE dp.id = %(period_id)s
            AND i.state in %(states)s
            AND i.type in %(invoice_types)s
            AND i.company_id = %(company_id)s
        ORDER BY i.date_invoice, i.internal_number
        """
        query_filters = {
            'period_id': self.period_id.id,
            'states': tuple(['open', 'paid']),
            'invoice_types': False,
            'company_id': self.company_id.id,
        }
        query_filters.update(kwargs)
        self._cr.execute(query, query_filters)
        fetch = self._cr.fetchall()
        inv_ids = [row[0] for row in fetch]
        invoice_model = self.env['account.invoice']
        invoices = invoice_model.browse(inv_ids)
        return invoices
