##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from string import ascii_uppercase
import logging

from odoo import models, _
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


def int2xlscol(number, state=None):
    if state is None:
        state = []
    alpsize = ascii_uppercase.__len__()
    q, r = divmod(number, alpsize)
    if q == 0:
        state.append(ascii_uppercase[r])
        return ''.join(reversed(state))
    state.append(ascii_uppercase[r])
    state = int2xlscol(q-1, state)
    return state


class SubjournalXlsx(models.AbstractModel):
    _name = 'report.report_xlsx.move_line_list_subj'
    _inherit = 'report.report_xlsx.abstract'

    def get_title(self, obj):
        if obj.based_on == 'sale':
            sub_type = 'Ventas'
        else:
            sub_type = 'Compras'

        title = 'Reporte - IVA %s Periodo %s a %s' % (sub_type, obj.date_from,
                                                      obj.date_to)
        return title

    def _get_types(self, obj):
        if obj.based_on == 'sale':
            return ['out_invoice', 'out_refund', 'out_debit']
        else:
            return ['in_invoice', 'in_refund', 'in_debit']

    def get_invoice_type(self, inv_type, denom, is_debit):
        if inv_type in ('out_invoice', 'in_invoice'):
            if is_debit:
                fiscal_type = "ND"
            else:
                fiscal_type = "F"
        else:
            fiscal_type = "NC"
        return '%s %s' % (fiscal_type, denom)

    def get_columns(self, types, obj):
        invoice_model = self.env['account.invoice']
        tax_model = self.env['account.tax']
        invoices = invoice_model.search([
            ('type', 'in', types),
            ('move_id.line_ids.date', '>=', obj.date_from),
            ('move_id.line_ids.date', '<=', obj.date_to)])
        tax_ids = set(
            invoices.mapped('move_id.line_ids.tax_ids').ids +
            invoices.mapped('move_id.line_ids.tax_line_id').ids)
        taxes = tax_model.browse(tax_ids)

        all_taxes = []
        i = 0
        base_first = obj.base_position == 'first'

        for tax in taxes.sorted(lambda t: getattr(t, obj.sort_by)):
            perception_tax_group = self.env.ref(
                'l10n_ar_perceptions_basic.tax_group_perceptions')
            if not (tax.tax_group_id and
                    tax.tax_group_id == perception_tax_group) and \
                    base_first:
                base_vals = {
                    'id': tax.id,
                    'is_exempt': tax.is_exempt,
                    'name': 'Base '+tax.name,
                    'type': 'base',
                    'column': 7+i,
                }
                all_taxes.append(base_vals)
                i += 1

            tax_vals = {
                'id': tax.id,
                'is_exempt': tax.is_exempt,
                'name': tax.name,
                'type': 'tax',
                'column': 7+i,
            }
            all_taxes.append(tax_vals)
            i += 1

            if not (tax.tax_group_id and
                    tax.tax_group_id == perception_tax_group) and \
                    not base_first:
                base_vals = {
                    'id': tax.id,
                    'is_exempt': tax.is_exempt,
                    'name': 'Base '+tax.name,
                    'type': 'base',
                    'column': 7+i,
                }
                all_taxes.append(base_vals)
                i += 1

        self.columns = all_taxes
        return all_taxes

    def get_lines(self, types, obj):
        q = """
        WITH all_lines AS (
            SELECT  l.move_id AS move_id,
                    lc.name AS company_id,
                    i.date_invoice AS date,
                    i.id AS invoice_id,
                    i.internal_number AS invoice_number,
                    i.type AS invoice_type,
                    i.cae AS cae,
                    i.cae_due_date AS cae_due_date,
                    i.is_debit_note AS is_debit_note,
                    id.name AS denomination,
                    CASE WHEN pos.name IS NOT NULL
                    THEN pos.name
                    ELSE split_part(i.internal_number, '-', 1) END AS pos,
                    l.id AS line_id,
                    l.tax_line_id AS tax_line_id,
                    l.credit AS credit,
                    l.debit AS debit,
                    l.tax_base_amount AS tax_amount,
                    p.id AS partner_id,
                    afp.name AS fiscal_position,
                    afp.id AS fpid,
                    rp.name AS partner,
                    rp.vat AS vat,
                    rpt.name AS partner_title,
                    rcs.name AS state,
                    amlatr.account_tax_id AS tax_ids
            FROM account_move_line l
            JOIN account_invoice i ON i.move_id = l.move_id
            JOIN invoice_denomination id ON id.id = i.denomination_id
            JOIN res_partner rp ON rp.id = i.partner_id
            LEFT JOIN res_country_state rcs ON rcs.id = rp.state_id
            LEFT JOIN res_partner_title rpt ON rpt.id = rp.title
            LEFT JOIN pos_ar pos ON pos.id = i.pos_ar_id
            JOIN res_partner p ON p.id = i.partner_id
            JOIN account_account a ON a.id = l.account_id
            JOIN account_fiscal_position afp ON afp.id = i.fiscal_position_id
            LEFT JOIN account_move_line_account_tax_rel amlatr
            ON (amlatr.account_move_line_id,amlatr.account_tax_id)=(
                SELECT account_move_line_id, account_tax_id
                FROM account_move_line_account_tax_rel amlatr
                WHERE account_move_line_id=l.id
                LIMIT 1
            )
            INNER JOIN res_company lc
            ON i.company_id = lc.id
            WHERE i.type IN %(inv_type)s
                AND l.date BETWEEN %(date_from)s AND %(date_to)s
                AND a.internal_type NOT IN ('payable', 'receivable')
                AND l.company_id IN %(company_ids)s
        ),
        grouped_invoice AS (
            SELECT invoice_id, ABS(SUM(debit - credit)) AS invoice_total
            FROM all_lines
            GROUP BY invoice_id
        )

        SELECT NULL AS move_id,
            al.date AS date,
            al.company_id AS company_id,
            -1 AS invoice_id,
            al.invoice_type AS invoice_type,
            NULL AS cae,
            NULL AS cae_due_date,
            NULL AS is_debit_note,
            'B' AS denomination,
            al.pos AS pos,
            MIN(al.invoice_number) AS inv_from,
            MAX(al.invoice_number) AS inv_to,
            NULL AS invoice_number,
            NULL AS line_id,
            al.tax_line_id AS tax_line_id,
            SUM(al.credit) AS credit,
            SUM(al.debit) AS debit,
            SUM(al.tax_amount) AS tax_amount,
            NULL AS partner_id,
            al.fiscal_position AS fiscal_position,
            al.fpid AS fpid,
            NULL AS partner,
            NULL AS vat,
            NULL AS partner_title,
            NULL AS state,
            NULL AS tax_ids
        FROM all_lines al
        JOIN grouped_invoice gi ON gi.invoice_id = al.invoice_id
        WHERE al.fpid = %(fiscal_id)s
            AND gi.invoice_total < %(grouped_max)s
            AND %(grouped)s
        GROUP BY al.date, al.tax_line_id, al.fpid,
            al.invoice_type, al.pos, al.fiscal_position, al.company_id

        UNION

        SELECT al.move_id AS move_id,
            al.date AS date,
            al.company_id AS company,
            al.invoice_id AS invoice_id,
            al.invoice_type AS invoice_type,
            al.cae AS cae,
            al.cae_due_date AS cae_due_date,
            al.is_debit_note AS is_debit_note,
            al.denomination AS denomination,
            al.pos AS pos,
            al.invoice_number AS inv_from,
            al.invoice_number AS inv_to,
            al.invoice_number AS invoice_number,
            al.line_id AS line_id,
            al.tax_line_id AS tax_line_id,
            al.credit AS credit,
            al.debit AS debit,
            al.tax_amount AS tax_amount,
            al.partner_id AS partner_id,
            al.fiscal_position AS fiscal_position,
            al.fpid AS fpid,
            al.partner AS partner,
            al.vat AS vat,
            al.partner_title AS partner_title,
            al.state AS state,
            al.tax_ids AS tax_ids
        FROM all_lines al
        JOIN grouped_invoice gi ON gi.invoice_id = al.invoice_id
        WHERE al.fpid = %(fiscal_id)s
            OR gi.invoice_total >= %(grouped_max)s
            OR NOT %(grouped)s

        ORDER BY date, pos, invoice_id, invoice_type
        """
        final_consumer = self.env.ref(
            'l10n_ar_point_of_sale.fiscal_position_final_cons')
        if obj.company_ids:
            company_ids = obj.company_ids.ids
        else:
            company_ids = self.env['res.company'].search([]).ids
        q_vals = {
            'inv_type': tuple(types),
            'date_from': obj.date_from,
            'company_ids': tuple(company_ids),
            'date_to': obj.date_to,
            'grouped': obj.grouped,
            'grouped_max': obj.grouped_max_amount,
            'fiscal_id': final_consumer.id,
        }
        self._cr.execute(q, q_vals)
        # Obtenemos el resultado de la consulta
        res = self._cr.dictfetchall()

        # TODO: FIX RAISE USERERROR
        if not len(res):
            raise UserError(
                _('There were no moves for this period'))

        self.c_taxes = [0] * len(self.columns)
        lines = {}
        for l in res:
            sign = 1
            sign_no_taxed = 1
            based_sign = 1

            if l['invoice_type'] in ('out_refund', 'in_refund'):
                sign = -1
            if l['invoice_type'] in ('out_invoice', 'in_refund'):
                sign_no_taxed = -1
            if obj.based_on == 'purchase':
                based_sign = -1

            dict_hash = (l['date'], l['invoice_type'],
                         l['pos'], l['invoice_id'])
            if dict_hash not in lines:
                lines[dict_hash] = l

                if l['invoice_id'] == -1:
                    l['partner'] = 'Agrupado %s monto menor a %s' % \
                        (l['fiscal_position'], obj.grouped_max_amount)
                    l['invoice_number'] = l['inv_from'] + ' -> ' + l['inv_to']

                l['taxes'] = [0] * len(self.columns)
                l['no_taxed'] = not l['tax_line_id'] and not l['tax_ids'] and (
                    l['debit'] - l['credit']) * sign * sign_no_taxed or 0.0
                l['total'] = (l['credit'] - l['debit']) * based_sign
                l['invoice_type'] = self.get_invoice_type(
                    l['invoice_type'], l['denomination'], l['is_debit_note'])
            else:
                ll = lines[dict_hash]
                ll['total'] += (l['credit'] - l['debit']) * based_sign
                ll['no_taxed'] += not l['tax_line_id'] and \
                    not l['tax_ids'] and \
                    (l['debit'] - l['credit']) * sign * sign_no_taxed or 0.0

            for i, tax in enumerate(self.columns):
                if l['tax_line_id'] == tax['id'] or (
                        l['tax_ids'] == tax['id'] and tax.get('is_exempt')):
                    if lines[dict_hash]['taxes'][i] == 0:
                        if tax['type'] == 'tax':
                            lines[dict_hash]['taxes'][i] = (
                                l['credit'] - l['debit']) * based_sign
                        elif tax['type'] == 'base':
                            lines[dict_hash]['taxes'][i] = \
                                l['tax_amount'] * sign
                    else:
                        if tax['type'] == 'tax':
                            lines[dict_hash]['taxes'][i] += (
                                l['credit'] - l['debit']) * based_sign
                        elif tax['type'] == 'base':
                            lines[dict_hash]['taxes'][i] += \
                                l['tax_amount'] * sign
                    if lines[dict_hash]['taxes'][i] != 0:
                        self.c_taxes[i] += 1

        res = [v for k, v in lines.items()]
        res2 = sorted(res, key=lambda k: k['date'] +
                      k['invoice_type'] +
                      k['invoice_number'][:4] +
                      ('0' if k['partner'].startswith('Agrupado') else '1') +
                      k['invoice_number'])
        return res2

    def _report_xls_fields(self):
        base_lst = [
            'Fecha', 'Compañía', 'Razon Social', 'Provincia', 'CUIT',
            'Cond. IVA', 'Tipo', 'Numero', 'No Gravado', 'Total'
        ]
        config_obj = self.env['ir.config_parameter']
        config_param = config_obj.sudo().get_param('subjournal_export_cae')
        if config_param:
            base_lst.insert(6, 'cae')
            base_lst.insert(7, 'cae_due_date')
        return base_lst

    def set_column(self, worksheet, index):
        worksheet.set_column('A:A', 10)
        worksheet.set_column('B:C', 20)
        worksheet.set_column('D:E', 10)
        worksheet.set_column('F:F', 5)
        worksheet.set_column('G:G', 10)
        worksheet.set_column('G:'+int2xlscol(index), 10)

    def create_format(self, workbook, bold, border_type,
                      border_color, back_color):
        _format = workbook.add_format({
            'bold': bold,
            'bg_color': back_color,
            'font_size': 10,
            'font_name': 'Arial',
        })
        _format.set_bottom(border_type)
        _format.set_bottom_color(border_color)
        _format.set_top(border_type)
        _format.set_top_color(border_color)
        _format.set_left(border_type)
        _format.set_left_color(border_color)
        _format.set_right(border_type)
        _format.set_right_color(border_color)
        return _format

    def generate_xlsx_report(self, workbook, data, obj):
        # Formats
        head_format = self.create_format(workbook, True, 1,
                                         '#C0C0C0', '#ffffb3')
        date_format = self.create_format(workbook, False, 1,
                                         '#C0C0C0', '#ffffff')
        gray_format = self.create_format(workbook, False, 1,
                                         '#C0C0C0', '#eaeaea')
        footer_format = self.create_format(workbook, True, 1,
                                           '#C0C0C0', '#ffd6cc')

        wizard_obj = self.env['account.tax.subjournal'].browse(obj.id)
        types = self._get_types(wizard_obj)
        wanted_list = self._report_xls_fields()
        title = self.get_title(wizard_obj)
        cols = self.get_columns(types, wizard_obj)
        lines = self.get_lines(types, wizard_obj)
        for i, col in enumerate(cols):
            if self.c_taxes[i] > 0:
                wanted_list.insert(-2, col['name'])
        sheet = workbook.add_worksheet(title)
        sheet.set_column('A:L', 20)
        for i, column in enumerate(wanted_list):
            sheet.write(int2xlscol(i)+'1', column, head_format)
        self.set_column(sheet, i)
        for p, line in enumerate(lines):
            p += 2
            cell_format = gray_format
            if p % 2:
                cell_format = date_format
            sheet.write('A'+str(p), line['date'], cell_format)
            sheet.write('B'+str(p), line['company_id'], cell_format)
            sheet.write('C'+str(p), line['partner'], cell_format)
            sheet.write('D'+str(p), line['state'], cell_format)
            sheet.write('E'+str(p), line['vat'], cell_format)
            sheet.write('F'+str(p), line['fiscal_position'], cell_format)
            sheet.write('G'+str(p), line['invoice_type'], cell_format)
            sheet.write('H'+str(p), line['invoice_number'], cell_format)
            i = 8
            for t, tax in enumerate(cols):
                if self.c_taxes[t] > 0:
                    sheet.write(int2xlscol(i)+str(p), line['taxes'][t],
                                cell_format)
                    i += 1
            sheet.write(int2xlscol(i)+str(p), line['no_taxed'], cell_format)
            sheet.write(int2xlscol(i+1)+str(p), line['total'], cell_format)

        # Formulas
        fac_formula = '{=SUMIF(G2:G%(last_line)s,"F *",%(col)s2:%(col)s%(last_line)s) + SUMIF(G2:G%(last_line)s,"ND *",%(col)s2:%(col)s%(last_line)s)}'  # noqa
        nc_formula = '{=SUMIF(G2:G%(last_line)s,"NC *",%(col)s2:%(col)s%(last_line)s)}'  # noqa
        total_formula = '{=SUM(%(col)s2:%(col)s%(last_line)s)}'  # noqa

        last_row_num = len(lines) + 1
        last_row_char = str(last_row_num)
        fac_row_char = str(last_row_num + 3)
        nc_row_char = str(last_row_num + 4)
        total_row_char = str(last_row_num + 5)

        i = -1
        for j, col in enumerate(cols):
            if self.c_taxes[j] > 0:
                col_char = int2xlscol(col['column']-i)
                indexes = {
                    'last_line': last_row_char,
                    'col': col_char,
                }

                # Fac
                sheet.write_formula(
                    col_char + fac_row_char,
                    fac_formula % indexes,
                    footer_format)

                # NC
                sheet.write_formula(
                    col_char + nc_row_char,
                    nc_formula % indexes,
                    footer_format)

                # Totals
                sheet.write_formula(
                    col_char + total_row_char,
                    total_formula % indexes,
                    footer_format)

            else:
                i += 1

        ng_col_char = int2xlscol(7+len(cols)-i)
        tot_col_char = int2xlscol(8+len(cols)-i)

        indexes = {
            'last_line': last_row_char,
        }
        indexes.update({'col': ng_col_char})
        # Fac NoGravado
        sheet.write_formula(
            ng_col_char + fac_row_char,
            fac_formula % indexes,
            footer_format)

        # NC NoGravado
        sheet.write_formula(
            ng_col_char + nc_row_char,
            nc_formula % indexes,
            footer_format)

        # Total NoGravado
        sheet.write_formula(
            ng_col_char + total_row_char,
            total_formula % indexes,
            footer_format)

        indexes.update({'col': tot_col_char})
        # Fac Total
        sheet.write_formula(
            tot_col_char + fac_row_char,
            fac_formula % indexes,
            footer_format)

        # NC Total
        sheet.write_formula(
            tot_col_char + nc_row_char,
            nc_formula % indexes,
            footer_format)

        # Total Final
        sheet.write_formula(
            tot_col_char + total_row_char,
            total_formula % indexes,
            footer_format)

        # formula labels
        sheet.write('A'+fac_row_char, 'Subtotal FC/ND', footer_format)
        sheet.write('A'+nc_row_char, 'Subtotal NC', footer_format)
        sheet.write('A'+total_row_char, 'Total', footer_format)
        # Footer format
        indexes = {
            'fac_row': fac_row_char,
            'last_col': tot_col_char,
            'last_row': total_row_char,
        }
        c_range = 'A%(fac_row)s:%(last_col)s%(last_row)s'
        sheet.conditional_format(c_range % indexes, {
            'type': 'cell',
            'criteria': '=',
            'value': 0,
            'format': footer_format})
