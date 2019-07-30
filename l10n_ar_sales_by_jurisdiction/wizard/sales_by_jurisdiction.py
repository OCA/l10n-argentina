##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import models, fields, _, api


class ExportSalesByJurisdictionXLS(models.TransientModel):
    _name = 'export.sales.by.jurisdiction.xls'
    _description = 'Export Sales By Jurisdiction'

    period_from = fields.Many2one(
        'date.period', string='Period From', required=True)
    period_to = fields.Many2one(
        'date.period', string='Period To', required=True)
    company_ids = fields.Many2many(
        'res.company', string='Company')

    @api.multi
    def xls_export(self):
        return self.print_report()

    def print_report(self):
        company_name = self.env.user.company_id.name
        print_by = self.env.user.name
        report_name = 'l10n_ar_sales_by_jurisdiction.sales_export_xlsx'

        period_from = self.period_from
        period_to = self.period_to

        datas = {
            'print_by': print_by,
            'date_start': period_from.date_from,
            'date_stop': period_to.date_to,
            'company_name': company_name,
        }

        report_file_name = _('sales.by.jurisdiction')
        company_ids = self.company_ids
        if not company_ids:
            company_ids = self.env['res.company'].search([])
        for company in company_ids:
            report_file_name += '_' + company.name
        data_return = {
            'type': 'ir.actions.report',
            'report_name': report_name,
            'report_type': 'xlsx',
            'context': dict(self.env.context, report_file=report_file_name),
            'data': {'dynamic_report': True},
            'datas': datas,
        }
        data_return['context'].update({'company_name': company_name})
        return data_return
