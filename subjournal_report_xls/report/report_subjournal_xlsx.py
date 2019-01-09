###############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (Cardozo Nicolás Joaquin)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from odoo import models, _
from odoo.exceptions import UserError


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
        q = """
        SELECT DISTINCT at.id
        FROM account_tax at
        LEFT JOIN account_move_line l ON l.tax_line_id = at.id
        LEFT JOIN account_move_line_account_tax_rel tr
            ON tr.account_tax_id = at.id
        LEFT JOIN account_invoice i ON i.move_id = l.move_id
        WHERE l.date BETWEEN %(date_from)s AND %(date_to)s
        AND i.type IN %(inv_type)s
        AND at.id IN (
            SELECT tax_code_id
            FROM subjournal_report_taxcode_column
            WHERE report_config_id=%(report_id)s
        ) ORDER BY at.id
        """
        q_vals = {
            'date_from': obj.date_from,
            'date_to': obj.date_to,
            'inv_type': tuple(types),
            'report_id': obj.report_config_id.id,
        }
        self._cr.execute(q, q_vals)
        res = self._cr.dictfetchall()

        ids = map(lambda x: x['id'], res)
        tax_code_column_model = self.env['subjournal.report.taxcode.column']
        taxes_config = tax_code_column_model.search(
            [('report_config_id', '=', obj.report_config_id.id)])
        taxes = self.env['account.tax'].browse(ids)
        all_taxes = []
        i = 0
        for tax in taxes.sorted(key=lambda x: taxes_config.filtered(
                lambda y: y.tax_code_id == x).sequence):
            all_taxes.append({
                'id': tax.id,
                'name': tax.name,
                'type': 'tax',
                'column': 72+i,
            })
            perception_tax_group = self.env.ref(
                'l10n_ar_perceptions_basic.tax_group_perceptions')
            i += 1
            if tax.tax_group_id and tax.tax_group_id == perception_tax_group:
                continue
            else:
                all_taxes.append({
                    'id': tax.id,
                    'name': 'Base '+tax.name,
                    'type': 'base',
                    'column': 72+i,
                })
                i += 1
        self.columns = all_taxes
        return all_taxes

    def get_lines(self, types, obj):
        q = """
        WITH all_lines AS (
            SELECT  l.move_id AS move_id,
                    l.date AS date,
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
            LEFT JOIN account_move_line_account_tax_rel amlatr ON (amlatr.account_move_line_id,amlatr.account_tax_id)=(
                SELECT account_move_line_id, account_tax_id FROM account_move_line_account_tax_rel amlatr WHERE account_move_line_id=l.id
                LIMIT 1
            )
            WHERE i.type IN %(inv_type)s
                AND l.date BETWEEN %(date_from)s AND %(date_to)s
                AND a.internal_type NOT IN ('payable', 'receivable')
        ),
        grouped_invoice AS (
            SELECT invoice_id, ABS(SUM(debit - credit)) AS invoice_total
            FROM all_lines
            GROUP BY invoice_id
        )

        SELECT NULL AS move_id,
            al.date AS date,
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
            al.invoice_type, al.pos, al.fiscal_position

        UNION

        SELECT al.move_id AS move_id,
            al.date AS date,
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
        q_vals = {
            'inv_type': tuple(types),
            'date_from': obj.date_from,
            'date_to': obj.date_to,
            'grouped': obj.grouped,
            'grouped_max': obj.grouped_max_amount,
            'fiscal_id': final_consumer.id,
        }
        self._cr.execute(q, q_vals)
        # Obtenemos el resultado de la consulta
        res = self._cr.dictfetchall()

        if not len(res):
            raise UserError(
                _('There were no moves for this period'))

        self.c_taxes = [0] * len(self.columns)
        lines = {}
        for l in res:
            sign = 1
            sign_no_taxed = 1
            if l['invoice_type'] in ('out_refund', 'in_refund'):
                sign = -1
            if l['invoice_type'] in ('out_invoice', 'in_refund'):
                sign_no_taxed = -1

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
                l['total'] = abs(l['debit'] - l['credit']) * sign
                l['invoice_type'] = self.get_invoice_type(
                    l['invoice_type'], l['denomination'], l['is_debit_note'])
            else:
                ll = lines[dict_hash]
                ll['total'] += abs(l['debit'] - l['credit']) * sign
                ll['no_taxed'] += not l['tax_line_id'] and not l['tax_ids'] and (
                    l['debit'] - l['credit']) * sign * sign_no_taxed or 0.0

            for i, tax in enumerate(self.columns):
                if l['tax_line_id'] == tax['id']:
                    if lines[dict_hash]['taxes'][i] == 0:
                        if tax['type'] == 'tax':
                            lines[dict_hash]['taxes'][i] = abs(
                                l['debit'] - l['credit'])*sign
                        elif tax['type'] == 'base':
                            lines[dict_hash]['taxes'][i] = \
                                l['tax_amount'] * sign
                    else:
                        if tax['type'] == 'tax':
                            lines[dict_hash]['taxes'][i] += abs(
                                l['debit'] - l['credit'])*sign
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

    def set_column(self, worksheet, index):
        worksheet.set_column('A:A', 10)
        worksheet.set_column('B:C', 20)
        worksheet.set_column('D:E', 10)
        worksheet.set_column('F:F', 5)
        worksheet.set_column('G:G', 10)
        worksheet.set_column('G:'+chr(index), 10)

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
        footer_format = self.create_format(workbook, True, 1,
                                           '#C0C0C0', '#ffd6cc')

        move_obj = self.env['account.move.line']
        wizard_obj = self.env['account.tax.subjournal'].browse(obj.id)
        types = self._get_types(wizard_obj)
        wanted_list = move_obj._report_xls_fields()
        title = self.get_title(wizard_obj)
        cols = self.get_columns(types, wizard_obj)
        lines = self.get_lines(types, wizard_obj)
        for i, col in enumerate(cols):
            if self.c_taxes[i] > 0:
                wanted_list.insert(-2, col['name'])
        sheet = workbook.add_worksheet(title)
        sheet.set_column('A:L', 20)
        i = 65
        for column in wanted_list:
            sheet.write(chr(i)+'3', column, head_format)
            i += 1
        self.set_column(sheet, i)
        for p, line in enumerate(lines):
            p += 4
            sheet.write('A'+str(p), line['date'], date_format)
            sheet.write('B'+str(p), line['partner'], date_format)
            sheet.write('C'+str(p), line['state'], date_format)
            sheet.write('D'+str(p), line['vat'], date_format)
            sheet.write('E'+str(p), line['fiscal_position'], date_format)
            sheet.write('F'+str(p), line['invoice_type'], date_format)
            sheet.write('G'+str(p), line['invoice_number'], date_format)
            i = 72
            for t, tax in enumerate(cols):
                if self.c_taxes[t] > 0:
                    sheet.write(chr(i)+str(p), line['taxes'][t], date_format)
                    i += 1
            sheet.write(chr(i)+str(p), line['no_taxed'], date_format)
            sheet.write(chr(i+1)+str(p), line['total'], date_format)

        # Formulas
        i = 0
        for j, col in enumerate(cols):
            if self.c_taxes[j] > 0:
                formula = '{=SUMIF('+chr(col['column']-i)+'4:'+chr(col['column']-i)+str(len(lines)+3)+',">0",'+chr(col['column']-i)+'4:'+chr(col['column']-i)+str(len(lines)+3)+')}'  # noqa
                sheet.write_formula(chr(col['column']-i)+str(len(lines)+4), formula, footer_format)  # noqa
                formula = '{=SUMIF('+chr(col['column']-i)+'4:'+chr(col['column']-i)+str(len(lines)+3)+',"<0",'+chr(col['column']-i)+'4:'+chr(col['column']-i)+str(len(lines)+3)+')}'  # noqa
                sheet.write_formula(chr(col['column']-i)+str(len(lines)+5), formula, footer_format)  # noqa
                formula = '{=SUM('+chr(col['column']-i)+'4:'+chr(col['column']-i)+str(len(lines)+3)+')}'  # noqa
                sheet.write_formula(chr(col['column']-i)+str(len(lines)+6), formula, footer_format)  # noqa
            else:
                i += 1
        # sumif '>0'
        column = chr(72+len(cols)-i)
        formula = '{=SUMIF('+column+'4:'+column+str(len(lines)+3)+',">0",'+column+'4:'+column+str(len(lines)+3)+')}'  # noqa
        sheet.write_formula(column+str(len(lines)+4), formula, footer_format)
        column = chr(73+len(cols)-i)
        formula = '{=SUMIF('+column+'4:'+column+str(len(lines)+3)+',">0",'+column+'4:'+column+str(len(lines)+3)+')}'  # noqa
        sheet.write_formula(column+str(len(lines)+4), formula, footer_format)
        # sumif '<0'
        column = chr(72+len(cols)-i)
        formula = '{=SUMIF('+column+'4:'+column+str(len(lines)+3)+',"<0",'+column+'4:'+column+str(len(lines)+3)+')}'  # noqa
        sheet.write_formula(column+str(len(lines)+5), formula, footer_format)
        column = chr(73+len(cols)-i)
        formula = '{=SUMIF('+column+'4:'+column+str(len(lines)+3)+',"<0",'+column+'4:'+column+str(len(lines)+3)+')}'  # noqa
        sheet.write_formula(column+str(len(lines)+5), formula, footer_format)
        # sum all
        column = chr(72+len(cols)-i)
        formula = '{=SUM('+column+'4:'+column+str(len(lines)+3)+')}'
        sheet.write_formula(column+str(len(lines)+6), formula, footer_format)
        column = chr(73+len(cols)-i)
        formula = '{=SUM('+column+'4:'+column+str(len(lines)+3)+')}'
        sheet.write_formula(column+str(len(lines)+6), formula, footer_format)
        # formula labels
        sheet.write('A'+str(len(lines)+4), 'Subtotal FC/ND', footer_format)
        sheet.write('A'+str(len(lines)+5), 'Subtotal NC', footer_format)
        sheet.write('A'+str(len(lines)+6), 'Total', footer_format)
        # Footer format
        c_range = 'A'+str(len(lines)+4)+':'+column+str(len(lines)+6)
        sheet.conditional_format(c_range, {
            'type': 'cell',
            'criteria': '=',
            'value': 0,
            'format': footer_format})
