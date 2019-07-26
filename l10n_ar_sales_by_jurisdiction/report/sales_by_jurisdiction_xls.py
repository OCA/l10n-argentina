##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from datetime import datetime

from odoo import models, _


class SalesExportXlsx(models.AbstractModel):
    _name = 'report.l10n_ar_sales_by_jurisdiction.sales_export_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_ws_params(self, wb, data, lines):
        self.cell_format = wb.add_format()
        self.cell_format.set_align("right")
        self.cell_format.set_num_format = "#,##0.00"

        # Add formula to cell
        self.formula_format = wb.add_format()
        self.formula_format.set_bold()
        self.formula_format.set_bg_color('#FFFFCC')
        self.formula_format.set_align("right")
        self.formula_format.set_num_format = "#.##0,00"

        sales_template = {
            'fecha': {
                'header': {
                    'value': 'Fecha',
                },
                'data': {
                    'value': self._render("line['fecha']"),
                },
                'width': 20,
            },
            'factura': {
                'header': {
                    'value': 'Factura',
                },
                'data': {
                    'value': self._render("line['invoice_internal_number']"),
                },
                'width': 20,
            },
            'fecha_asiento': {
                'header': {
                    'value': 'Fecha asiento',
                },
                'data': {
                    'value': self._render("line['fecha_asiento']"),
                },
                'width': 20,
            },
            'nombre_cliente': {
                'header': {
                    'value': 'Nombre cliente',
                },
                'data': {
                    'value': self._render("line['nombre_cliente']"),
                },
                'width': 20,
            },
            'jurisdiccion': {
                'header': {
                    'value': 'Jurisdicción',
                },
                'data': {
                    'value': self._render("line['jurisdiccion']"),
                },
                'width': 20,
            },
            'cp': {
                'header': {
                    'value': 'Código Postal',
                },
                'data': {
                    'value': self._render("line['cp']"),
                },
                'width': 20,
            },
            'codigo_cuenta': {
                'header': {
                    'value': 'Código cuenta',
                },
                'data': {
                    'value': self._render("line['codigo_cuenta']"),
                },
                'width': 20,
            },
            'nombre_cuenta_contable': {
                'header': {
                    'value': 'Nombre cuenta contable',
                },
                'data': {
                    'value': self._render("line['nombre_cuenta_contable']"),
                },
                'width': 22,
            },
            'monto': {
                'header': {
                    'value': 'Monto',
                },
                'data': {
                    'value': self._render("line['monto']"),
                    'format': self.cell_format,
                },
                'width': 20,
            },
        }
        self.sales_template = sales_template

        wanted_list = [
            'fecha',
            'factura',
            'fecha_asiento',
            'nombre_cliente',
            'jurisdiccion',
            'cp',
            'codigo_cuenta',
            'nombre_cuenta_contable',
            'monto',
        ]
        worksheets = []
        company_ids = lines.company_ids
        if not company_ids:
            company_ids = self.env['res.company'].search([])
        for company_id in company_ids:
            ws_params = {
                'company_id': company_id.id,
                'ws_name': company_id.name,
                'generate_ws_method': '_sales_report',
                'title': company_id.name + " " + _("Sales by jurisdiction"),
                'wanted_list': wanted_list,
                'col_specs': sales_template,
            }
            worksheets.append(ws_params)

        return worksheets

    def _print_jurisdiction_block(self, ws, row_pos, ws_params,
                                  jurisdiction, lines):
        row_pos += 1
        jurisdiction = jurisdiction or _("Undefined")
        ws.merge_range(
            row_pos, 0, row_pos, len(self.sales_template) - 1,
            jurisdiction, self.format_theader_yellow_left)
        row_pos += 1
        _from = row_pos
        jurisdiction_total = 0
        for line in lines:
            # Change date format to dd-mm-yyyy
            line['fecha'] = datetime.strftime(
                datetime.strptime(
                    line['fecha'], "%Y-%m-%d"),
                "%d-%m-%Y") if line['fecha'] else ''
            line['fecha_asiento'] = datetime.strftime(
                datetime.strptime(
                    line['fecha_asiento'], "%Y-%m-%d"),
                "%d-%m-%Y") if line['fecha_asiento'] else ''
            line['monto'] = float(line['monto'])
            row_pos = self._write_line(
                ws, row_pos, ws_params, col_specs_section='data',
                render_space={
                    'line': line,
                },
                default_format=self.format_tcell_left)
            jurisdiction_total += line['monto']

        ws.merge_range(
            row_pos, 0, row_pos, len(self.sales_template) - 2,
            _("Totals") + ': [%s]' % jurisdiction,
            self.format_theader_yellow_left)
        formula = '=SUM(I{_from}:I{to}'.format(_from=_from, to=row_pos)
        ws.write_formula(
            row_pos, len(self.sales_template) - 1, formula,
            self.formula_format, round(jurisdiction_total, 2))
        return (_from, row_pos, jurisdiction_total)

    def _sales_report(self, workbook, ws, ws_params, data, lines):
        lines = self.get_data(lines, ws_params['company_id'])
        ws.set_portrait()
        ws.fit_to_pages(1, 0)
        ws.set_header(self.xls_headers['standard'])
        ws.set_footer(self.xls_footers['standard'])

        self._set_column_width(ws, ws_params)

        row_pos = 0
        row_pos = self._write_ws_title(ws, row_pos, ws_params)
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_yellow_left)
        ws.freeze_panes(row_pos, 0)

        lines_by_jurisdictions = {}

        for line in lines:
            jurisdiction = line.get('jurisdiccion')
            lines_by_jurisdictions.setdefault(jurisdiction, [])
            lines_by_jurisdictions[jurisdiction].append(line)

        grand_total = 0
        block_info = []
        for jurisdiction, lines in lines_by_jurisdictions.items():
            init_row, row_pos, block_total = self._print_jurisdiction_block(
                ws, row_pos, ws_params, jurisdiction, lines)
            grand_total += block_total
            block_info.append((init_row, row_pos))
            row_pos += 1

        formula_row = row_pos + 1

        total_formula = "=" + " + ".join(
            map(lambda block: "SUM(I%s:I%s)" % (block[0], block[1]),
                block_info))

        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='footer',
            default_format=self.format_theader_yellow_left)
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='footer',
            default_format=self.format_theader_yellow_left)
        ws.write(
            formula_row, 0, _("Totals"), self.format_theader_yellow_left)
        ws.write_formula(
            formula_row, len(self.sales_template) - 1, total_formula,
            self.formula_format, round(grand_total, 2))

    def get_data(self, data, company):
        invoice_obj = self.env['account.invoice']

        select_extra, join_extra, where_extra, sort_selection = invoice_obj.\
            _report_xls_query_extra()

        date_start = data.period_from.date_from
        date_stop = data.period_to.date_to

        # SQL select for performance reasons, as a consequence, there are no
        # field value translations.
        # If performance is no issue, you can adapt the _report_xls_template in
        # an inherited module to add field value translations.
        query = """
        SELECT
            ai.id AS invoice_id,
            CASE
                WHEN ai.is_debit_note IS True THEN 'ND '
                WHEN ai.type = 'out_invoice' THEN 'FAC '
                ELSE 'NC ' END || id.name || ' ' ||
                ai.internal_number AS invoice_internal_number,
            ai.company_id AS company_id,
            rc.name AS company_name,
            ai.date_invoice AS Fecha,
            id.name AS Denom,
            pa.name AS Pto_Vta,
            ai.internal_number AS Num_Factura,
            am.date AS Fecha_Asiento,
            rp.name AS Nombre_Cliente,
            COALESCE(rcs2.name, rcs.name, rcs_def.name) AS Jurisdiccion,
            rp.zip AS CP,
            aa.code AS Codigo_Cuenta,
            aa.name AS Nombre_Cuenta_Contable,
            CASE WHEN ai.type = 'out_invoice'
                THEN ail.price_subtotal
            ELSE -ail.price_subtotal
            END AS Monto,
        CASE WHEN ai.is_debit_note IS True THEN 'Nota de Débito'
        WHEN ai.type = 'out_invoice' THEN 'Factura'
        ELSE 'Nota de Crédito' END AS TipoFactura
        """ + select_extra + """
        FROM account_invoice_line ail
        LEFT JOIN product_product pp
            ON pp.id = ail.product_id
        JOIN account_account aa
            ON aa.id = ail.account_id
        JOIN account_invoice ai
                ON ai.id = ail.invoice_id
        LEFT JOIN res_partner rp2
            ON ai.address_shipping_id = rp2.id
        JOIN res_company rc
            ON rc.id = ai.company_id
        JOIN account_move am
            ON am.id = ai.move_id
        LEFT JOIN res_partner rp
            ON rp.id = ai.partner_id
        LEFT JOIN res_country_state rcs
            ON rcs.id = rp.state_id
        LEFT JOIN res_country_state rcs2
            ON rcs2.id = rp2.state_id
        JOIN pos_ar pa
            ON pa.id = ai.pos_ar_id
        JOIN invoice_denomination id
            ON id.id = ai.denomination_id
        LEFT JOIN report_default_jurisdiction_configuration rdjc
            ON rdjc.pos_ar_id = pa.id
        LEFT JOIN res_country_state rcs_def
            ON rcs_def.id = rdjc.state_id
        """ + join_extra + """
        WHERE ai.date_invoice BETWEEN %(date_start)s AND %(date_stop)s
            AND ai.company_id = %(company_id)s
        AND ai.state IN ('open', 'paid')
        AND ai.type IN ('out_invoice', 'out_refund')
        """ + where_extra + """
        ORDER BY """ + sort_selection + """
        rcs.name, ai.date_invoice, ai.internal_number
        """
        query_vals = {
            'date_start': date_start,
            'date_stop': date_stop,
            'company_id': company,
        }
        self._cr.execute(query, query_vals)
        lines = self._cr.dictfetchall()

        return lines
