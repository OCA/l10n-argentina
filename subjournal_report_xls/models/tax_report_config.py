from odoo import fields, models


class TaxSubjournalReportConfig(models.Model):
    _name = 'tax.subjournal.report.config'
    _description = 'Tax Subjournal Report Configuration'

    name = fields.Char('Name', size=64)
    tax_report_id = fields.Many2one('ir.actions.report',
                                    string='Tax Report',
                                    required=True, index=True)
    tax_column_ids = fields.One2many('subjournal.report.taxcode.column',
                                     'report_config_id',
                                     string='Report Columns')
    based_on = fields.Selection([('sale', 'Sales'),
                                 ('purchase', 'Purchases')],
                                string='Based On',
                                required=True, default='sale')


class SubjournalReportTaxcodeColumn(models.Model):
    _name = 'subjournal.report.taxcode.column'
    _description = 'subjournal.report.taxcode.column'

    name = fields.Char(string='Name', size=32)
    report_config_id = fields.Many2one('tax.subjournal.report.config',
                                       ondelete='cascade')
    tax_code_id = fields.Many2one('account.tax', string='Tax Code')
    print_total = fields.Boolean(string='Print Total',
                                 help="If true, sum  Tax and Base amount. \
                                 You should use only Tax Code and not \
                                 Base Code if this is True.")
    sequence = fields.Integer(string='Sequence')
    # TODO: Como tenemos el campo based_on en el report_config, podriamos
    # filtrar los account_tax_code por los que se aplican a compras, pero
    # esa informacion esta en account_tax.
    # Tal vez, se tenga que quitar la relacion con tax_code_id y hacerlo
    # con account_tax que tiene el campo para diferenciar compras y ventas.
    # De esta manera es mas intuitivo, pero a su vez hay que modificar el
    # codigo de este objeto para agregarle unos booleanos que permitan
    # decidir si se imprime el tax y/o el base de ese account_tax configurado
    # como columna y tambien cambiar el parser.
    # Por ahora, se deja de esta manera, poco intuitivo, pero que funciona
    # correctamente si se configura correctamente.
