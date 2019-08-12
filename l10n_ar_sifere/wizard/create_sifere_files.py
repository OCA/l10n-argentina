##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from decimal import Decimal
import datetime
import re
import logging

from odoo import models, fields, api, _
from odoo.addons.base_report_exporter.utils.fixed_width \
    import FixedWidth, moneyfmt
from .fixed_width_dicts import HEAD_LINES_RET, HEAD_LINES_PER

logger = logging.getLogger(__name__)

vn_regex_pattern = r'[\s\D-]'


class CreateSifereRetentionFile(models.TransientModel):
    _name = 'create.sifere.retention.file'
    _desc = 'Create SIFERE Retention File'

    period_id = fields.Many2one('date.period', 'Period')
    notes = fields.Text('Notes')


class CreateSiferePerceptionFile(models.TransientModel):
    _name = 'create.sifere.perception.file'
    _desc = 'Create SIFERE Perception File'

    period_id = fields.Many2one('date.period', 'Period')
    notes = fields.Text('Notes')


class ReportFilesGenerator(models.Model):
    _inherit = 'report.files.generator'

    @api.multi
    def _do_sifere(self, method):
        data = getattr(self, method)()
        errors = data.get('errors')
        files = data.get('files')
        state = not bool(errors)

        ddict = {
            'state': state,
            'errors': errors,
            'files': files,
        }
        return ddict

    @api.multi
    def _do_sifere_ret(self):
        return self._do_sifere('create_retention_file')

    @api.multi
    def create_retention_file(self):
        period = self.period_id
        period_name = self.period_id.name
        period_start_date = self.period_id.date_from
        period_end_date = self.period_id.date_to
        company_id = self.env.user.company_id.id
        cr = self._cr

        retention_query = """
        SELECT r.id FROM retention_tax_line r
        JOIN retention_retention ret ON r.retention_id = ret.id
        JOIN account_tax at ON ret.tax_id=at.id
        WHERE r.date BETWEEN %(date_from)s AND %(date_to)s
        AND ret.type in ('gross_income') AND at.type_tax_use LIKE 'sale'
        AND r.company_id = %(company_id)s ORDER BY r.date
        """

        cr.execute(retention_query, {
            'date_from': period_start_date,
            'date_to': period_end_date,
            'company_id': company_id,
        })
        res = cr.fetchall()
        if not len(res):
            return {
                'errors': 'Applicable Retentions for export not found. ' +
                '\nHINT: Is there any IIBB retentions supported for this ' +
                'period?',
                'resource': self.period_id,
            }
        retention_ids = [retention_ids[0] for retention_ids in res]

        res = self._generate_retention_file(
            company_id, period.id, period_name, retention_ids)
        return res

    @api.model
    def _generate_retention_file(self, company, period_id,
                                 period_name, retention_ids):
        retention_tax_line_obj = self.env['retention.tax.line']
        sifere_jurisdiction_obj = self.env['sifere.jurisdiction']
        sifere_config = self.env['sifere.config'].search(
            [('name', '=', 'Default')])
        fixed_width = FixedWidth(HEAD_LINES_RET)

        regs = []
        errors = []
        for tax_line in retention_tax_line_obj.browse(retention_ids):
            # String(YYYY-MM-DD)->Datetime
            date = datetime.datetime.strptime(tax_line.date, '%Y-%m-%d')
            # Datetime->String: dd/mm/yyyy
            date = datetime.datetime.strftime(date, '%d/%m/%Y')
            tax_line_name = tax_line.get_readeable_name()
            logger.info('Processing %s' % tax_line_name)
            nro_doc_retenido = tax_line.partner_id.vat
            if not nro_doc_retenido:
                errors.append({
                    'errors': 'Partner VAT not found',
                    'resource': tax_line.partner_id,
                })
            if '-' not in nro_doc_retenido and len(nro_doc_retenido) == 11:
                nro_doc_retenido = '{0}-{1}-{2}'.format(
                    nro_doc_retenido[0:2], nro_doc_retenido[2:10],
                    nro_doc_retenido[10])
            jurisdiction = sifere_jurisdiction_obj.search(
                [('state', '=', tax_line.retention_id.state_id.id)])
            if not jurisdiction.code:
                jurisdiction_code = 0
                if not sifere_config.ignore_jurisdiction:
                    errors.append({
                        'errors': 'Jurisdiction cannot be found',
                        'resource': tax_line.retention_id,
                    })
            else:
                jurisdiction_code = jurisdiction.code

            number = tax_line.payment_order_id.number
            num_voucher = re.sub(vn_regex_pattern, '', number)
            num_constancia = re.sub(r'-', '0', tax_line.certificate_no or '')
            line = {
                'codigo_jurisdiccion': jurisdiction_code,
                'cuit': nro_doc_retenido,
                'fecha_retencion': date,
                'numero_sucursal': num_voucher[:4],
                'numero_constancia': num_constancia,
                'tipo_comprobante': 'O',
                'letra_comprobante': '',
                'num_comprobante_original': num_voucher,
                'monto_retencion': moneyfmt(Decimal(
                    tax_line.amount), places=2, ndigits=8, dp=','),
            }

            # Apendeamos el registro
            fixed_width.update(**line)
            regs.append(fixed_width.line)

        name = 'SIFERE_RET_%s.txt' % period_name

        data = {
            'errors': errors,
            'files': [{
                'name': name,
                'data': regs,
            }],
        }
        return data

    @api.multi
    def _do_sifere_per(self):
        return self._do_sifere('create_perception_file')

    @api.multi
    def create_perception_file(self):
        period = self.period_id
        period_name = self.period_id.name
        period_start_date = self.period_id.date_from
        period_end_date = self.period_id.date_to
        company_id = self.env.user.company_id.id
        cr = self._cr

        perception_query = """
        SELECT p.id FROM perception_tax_line p
        JOIN perception_perception per ON p.perception_id = per.id
        JOIN account_tax at ON per.tax_id=at.id
        JOIN account_invoice i ON p.invoice_id=i.id
        WHERE p.date BETWEEN %(date_from)s AND %(date_to)s
        AND i.state IN %(inv_state)s
        AND per.type in %(type)s AND at.type_tax_use LIKE 'purchase'
        AND p.company_id = %(company_id)s ORDER BY p.date
        """

        q_data = {
            'date_from': period_start_date,
            'date_to': period_end_date,
            'type': ('gross_income', ),
            'inv_state': ('open', 'paid', ),
            'company_id': company_id,
        }
        cr.execute(perception_query, q_data)
        res = cr.fetchall()
        if not len(res):
            return {
                'errors': _(
                    'Applicable Perception for export not found. \n ' +
                    'HINT: Is there any IIBB perception supported for ' +
                    'this period?'),
                'resource': self.period_id,
            }
        perception_ids = [perception_ids[0] for perception_ids in res]

        res = self._generate_perception_file(
            company_id, period.id, period_name, perception_ids)
        return res

    @api.model
    def _get_tipo_comprobante(self, invoice_id):
        res = None
        if invoice_id.type == 'in_invoice':
            if invoice_id.is_debit_note:
                res = 'D'
            else:
                res = 'F'
        elif invoice_id.type == 'in_refund':
            res = 'C'
        return res

    @api.model
    def _generate_perception_file(self, company, period_id,
                                  period_name, perception_ids):
        perception_tax_line_obj = self.env['perception.tax.line']
        sifere_jurisdiction_obj = self.env['sifere.jurisdiction']
        sifere_config = self.env['sifere.config'].search(
            [('name', '=', 'Default')])
        fixed_width = FixedWidth(HEAD_LINES_PER)

        regs = []
        errors = []
        for tax_line in perception_tax_line_obj.browse(perception_ids):
            # String(YYYY-MM-DD)->Datetime
            date = datetime.datetime.strptime(tax_line.date, '%Y-%m-%d')
            # Datetime->String: dd/mm/yyyy
            date = datetime.datetime.strftime(date, '%d/%m/%Y')
            tax_line_name = tax_line.get_readeable_name()
            logger.info('Processing %s' % tax_line_name)
            nro_doc_percibido = tax_line.partner_id.vat
            if not nro_doc_percibido:
                errors.append({
                    'errors': 'Partner VAT not found',
                    'resource': tax_line.partner_id,
                })
            if '-' not in nro_doc_percibido and len(nro_doc_percibido) == 11:
                nro_doc_percibido = '{0}-{1}-{2}'.format(
                    nro_doc_percibido[0:2], nro_doc_percibido[2:10],
                    nro_doc_percibido[10])
            jurisdiction = sifere_jurisdiction_obj.search(
                [('state', '=', tax_line.perception_id.state_id.id)])
            if not jurisdiction.code:
                jurisdiction_code = 0
                if not sifere_config.ignore_jurisdiction:
                    errors.append({
                        'errors': 'Jurisdiction cannot be found',
                        'resource': tax_line.perception_id,
                    })
            else:
                jurisdiction_code = jurisdiction.code

            internal_number_split = tax_line.invoice_id.internal_number.split(
                '-')
            tipo_cbte = self._get_tipo_comprobante(tax_line.invoice_id)
            if tipo_cbte == 'C':
                sign = -1
            else:
                sign = 1
            line = {
                'codigo_jurisdiccion': jurisdiction_code,
                'cuit': nro_doc_percibido,
                'fecha_percepcion': date,
                'numero_sucursal': internal_number_split[0],
                'numero_constancia': internal_number_split[1],
                'tipo_comprobante': tipo_cbte,
                'letra_comprobante': tax_line.invoice_id.denomination_id.name
                or '',
                'monto_percepcion': moneyfmt(Decimal(tax_line.amount) * sign,
                                             places=2, ndigits=9, dp=','),
            }

            # Apendeamos el registro
            fixed_width.update(**line)
            regs.append(fixed_width.line)

        name = 'SIFERE_PER_%s.txt' % period_name

        data = {
            'errors': errors,
            'files': {
                'name': name,
                'data': regs,
            },
        }
        return data
