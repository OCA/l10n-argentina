###############################################################################
#   Copyright (c) 2007-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from odoo import fields, models


class PerceptionPerception(models.Model):
    _name = "perception.perception"
    _description = "Perception Configuration"

    """Objeto que define las percepciones que pueden utilizarse

       Configura las percepciones posibles. Luego a partir de
       estos objetos se crean perception.tax que iran en las
       account.invoice. Además, se crean account_invoice_tax
       que serian percepciones que se realizan en una factura,
       ya sea, de proveedor o de cliente. Y a partir de estas se
       crean los asientos correspondientes. De este objeto se
       toma la configuracion para generar las perception.tax y
       las account.invoice.tax con datos como monto, base imponible,
       nro de certificado, etc.
    """

    name = fields.Char('Perception', required=True, size=64)
    tax_id = fields.Many2one('account.tax', string='Tax', required=True,
                             help="Tax configuration for this perception")
    type_tax_use = fields.Selection([('sale', 'Sales'),
                                     ('purchase', 'Purchases'),
                                     ('none', 'None')],
                                    related='tax_id.type_tax_use',
                                    readonly=True,
                                    string='Tax Application')
    state_id = fields.Many2one('res.country.state', 'State/Province')
    type = fields.Selection([('vat', 'VAT'),
                             ('gross_income', 'Gross Income'),
                             ('profit', 'Profit'),
                             ('other', 'Other')], 'Type', default='vat')
    jurisdiccion = fields.Selection([('nacional', 'Nacional'),
                                     ('provincial', 'Provincial'),
                                     ('municipal', 'Municipal')
                                     ], 'Jurisdiccion', default='nacional')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
