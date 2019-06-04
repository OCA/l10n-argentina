###############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (Cardozo Nicolás Joaquin)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from odoo import fields, models
import time


class AccountTaxSubjournal(models.TransientModel):
    _name = "account.tax.subjournal"
    _description = "Account tax subjournal report"

    def _get_report_id(self):
        report_id = self.env['ir.actions.report'].search(
            [('report_name', '=', 'report_xlsx.move_line_list_subj')])
        return report_id

    date_from = fields.Date(string='Start of period',
                            default=time.strftime('%Y-%m-01'))
    date_to = fields.Date(string='End of period',
                          default=fields.Datetime.now)
    report_id = fields.Many2one('ir.actions.report',
                                default=_get_report_id,
                                string='Report')
    based_on = fields.Selection([('sale', 'Sales'),
                                 ('purchase', 'Purchases')],
                                string='Based On', required=True,
                                default='sale')
    grouped = fields.Boolean(
        string="Grouped",
        help="Type B Invoices below the grouped max amount will be " +
        "grouped in a single line per day and tax.")
    grouped_max_amount = fields.Float(
        string="Grouped Max Amount",
        help="If grouped is checked, this will determine the " +
        "grouping threshold")
    sort_by = fields.Selection([
        ('sequence', 'Sequence'),
        ('name', 'Name')],
        string='Sort Taxes by', required=True,
        default='sequence')
    base_position = fields.Selection([
        ('first', 'First'),
        ('second', 'Second')],
        string='Base Column Position', required=True,
        default='first')

    company_ids = fields.Many2many('res.company', string = 'Company')

    def create_report(self):
        data = {'ids': self.ids}
        data['model'] = 'account.move.line'
        data['form'] = self.read()[0]
        return {
            'data': data,
            'type': 'ir.actions.report',
            'report_name': 'report_xlsx.move_line_list_subj',
            'report_type': 'xlsx',
            'report_file': 'export_subjournal',
            'name': 'Export Subjournal',
        }
