###############################################################################
#
#    Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)


class PerceptionPerception(models.Model):
    _name = "perception.perception"
    _inherit = "perception.perception"

    code = fields.Char('AFIP Code', required=False, size=32)
    general_resolution = fields.Char('GR Number', required=False, size=64)
    notes = fields.Text('Notes')
    vat_application_ids = fields.One2many(
        'perception.tax.application', 'perception_id',
        'VAT Tax Application', domain=[('type', '=', 'vat')])
    gi_application_ids = fields.One2many(
        'perception.tax.application', 'perception_id',
        'Gross Income Tax Application', domain=[('type', '=', 'gross_income')])
    profit_application_ids = fields.One2many(
        'perception.tax.application', 'perception_id',
        'Profit Tax Application', domain=[('type', '=', 'profit')])
    applicable_state = fields.Selection([
        ('dest', 'Destination'),
        ('source', 'Source'),
        ('always', 'Always')], 'Applicable State', default='dest',
        help="Indicates if this Perception is applicable when:\n"
        "* State/Province is equals to source address\n"
        "* State/Province is equals to destination address\n"
        "* Always")
    applicable_location = fields.Selection([
        ('invoice', _('Invoicing Address')),
        ('shipping', _('Shipping Address'))], 'Application Address',
        default='shipping',
        help="Indicates whether the Perception is applicable when:\n"
        "* The Invoicing Source/Destination address matches the State/Province\n"  # noqa
        "* The Shipping Source/Destination address matches the State/Province")  # noqa
    check_sit_iibb = fields.Boolean(
        'Check IIBB Situation', default=False,
        help="If checked, when IIBB situation is Multilateral, " +
        "this perception is always applicable")
    always_apply_padron = fields.Boolean(
        'Always Apply from Padron', default=False,
        help="If checked, when the partner has a perception exception " +
        "and it was generated from a padron, this perception will be applied")

    @api.model
    def _get_concepts_from_account(self, account):

        if not self or not account:
            return None

        concept_obj = self.env['perception.concept']

        account_id = account.id
        concepts = []

        query = "SELECT c.id FROM account_account a " \
                "JOIN account_perception_concept_rel arcl " \
                "ON arcl.account_id=a.id " \
                "JOIN perception_concept c ON c.id=arcl.concept_id " \
                "WHERE c.type=%s " \
                "AND a.id=%s"

        cr = self.env.cr
        cr.execute(query, (self.type, account_id,))

        res = cr.fetchall()
        if res:
            res = [r[0] for r in res]
            concepts = concept_obj.browse(res)
        else:
            raise ValidationError(
                _("Perception Error!\n" +
                  "Accont %s[%s] must have an associated concept for %s. " +
                  "Please configure it!") % (account.name, account.code,
                                             self.name))

        return concepts

    @api.model
    def _check_perception_applicable(self, invoice, perception_data):
        sit_iibb = perception_data['sit_iibb']
        from_padron = perception_data['from_padron']
        partner_obj = self.env['res.partner']
        sale_obj = self.env['sale.order']

        if not self.state_id:
            return True

        if self.applicable_state == 'always':
            return True

        if self.always_apply_padron and from_padron:
            return True

        # Chequeamos la situacion de IIBB,
        # si es CM, directamente retornamos True
        if self.check_sit_iibb:
            _logger.info("Chequeo de situacion IIBB activado")
            multilateral = self.env.ref(
                "l10n_ar_point_of_sale.iibb_situation_multilateral")
            if sit_iibb == multilateral:
                _logger.info("Partner es Convenio Multilateral, " +
                             "aplica Percepcion %s", self.name)
                return True

        # Si la jurisdiccion de aplicacion es la de origen
        partner_state = False
        perception_state = self.state_id.id

        if self.applicable_state == 'source':
            if self.applicable_location == 'invoice':
                partner_state = invoice.company_id.partner_id.state_id.id
                if not partner_state:
                    raise ValidationError(
                        _('Company Configuration Error!\n') +
                        _('There is no State/Province configured ' +
                          'for this Company'))

            elif self.applicable_location == 'shipping':
                origin_sales = sale_obj.search(
                    [('invoice_ids', 'in', invoice.ids)])
                warehouses = origin_sales.mapped('warehouse_id')
                wh_addresses = map(
                    lambda x: x.partner_id.address_get(
                        ['delivery'])['delivery'], warehouses)
                partner_state = map(lambda x: partner_obj.browse(
                    x).state_id.id, wh_addresses)

        elif self.applicable_state == 'dest':
            if self.applicable_location == 'invoice':
                partner_state = invoice.partner_id.state_id.id

            elif self.applicable_location == 'shipping':
                partner_state = invoice.address_shipping_id.state_id.id

            # Si el partner_dest_state sigue siendo False tomamos
            # la direccion de delivery del partner directamente
            if not partner_state:
                address_id = invoice.partner_id.address_get(
                    ['delivery'])['delivery']
                partner_state = partner_obj.browse(address_id).state_id.id
                if not partner_state:
                    raise ValidationError(
                        _('Warning!\n') +
                        _('Partner has no Delivery State configured. ' +
                          'To compute Perception, is needed to know ' +
                          'Delivery State. ' +
                          'Please, configure a Partner Address.'))

        # Hacemos el chequeo de los states
        if isinstance(partner_state, list):
            if perception_state not in partner_state:
                return False
        else:
            if perception_state != partner_state:
                return False

        return True

    @api.model
    def _compute_base_perception(self, invoice, perception_data):
        activity = perception_data['activity_id']
        percent = perception_data['percent']
        sit_iibb = perception_data['sit_iibb']
        tax_app_obj = self.env['perception.tax.application']

        concept_id = False

        # Obtenemos la actividad configurada para esta Percepcion en el partner
        activity_id = activity and activity.id or False

        # Por cada linea, nos fijamos la configuracion del producto
        perceptions = {}

        for line in invoice.invoice_line:
            account_id = line.account_id

            concepts = self._get_concepts_from_account(account_id)

            # Si algun concepto no esta sujeto a percepcion, continuamos
            no_subject = False
            for concept in concepts:
                if concept and concept.no_subject:
                    no_subject = True

            if no_subject:
                continue

            concept_name = ' '.join(map(lambda a: a.name, concepts))
            activity_name = activity and activity.name or ''
            concept_ids = concepts and map(lambda a: a.id, concepts) or []

            # Buscamos las taxapps que concuerden
            tapp_domain = [('perception_id', '=', self.id),
                           ('concept_id', 'in', concept_ids),
                           ('activity_id', '=', activity_id)]
            iibb_domain = []

            if self.type == 'gross_income':
                iibb_domain.append(
                    ('sit_iibb', '=', sit_iibb.id if sit_iibb else False))

            taxapps = tax_app_obj.search(tapp_domain+iibb_domain)

            # Si no se encuentra con la situacion de iibb,
            # buscamos normalmente, aplica regla general
            if not taxapps:
                tapp_domain.append(('sit_iibb', '=', False))
                taxapps = tax_app_obj.search(tapp_domain)

            if not taxapps:
                raise ValidationError(
                    _("Perception Error!\n") +
                    _("There is no configured a Perception Application (%s) " +
                      "that corresponds to\nActivity: %s \nConcept: %s\n for" +
                      " the Account %s") % (self.name, activity_name,
                                            concept_name, account_id.name))

            if len(taxapps) > 1:
                raise ValidationError(
                    _("Perception Error!\n") +
                    _("There is more than one Perception Application (%s) " +
                      "configured that corresponds to\nActivity: %s \n" +
                      "Concept: %s\n for the Account %s") % (
                          self.name, activity_name, concept_name,
                          account_id.name))

            concept_id = taxapps.concept_id.id

            # Obtenemos toda la info contable de la linea de factura
            # todas las cantidades y los impuestos de IVA aplicados
            res = line._compute_all_vat_taxes()[line.id]

            # Hacemos el computo de la Percepcion por linea de factura
            base = taxapps.compute_base(percent, res)

            if base == 0.0:
                continue

            # Luego vamos agrupando por Concepto (no por actividad)
            if concept_id in perceptions:
                perceptions[concept_id]['base'] += base
                # perceptions[concept_id]['amount'] += amount
                perceptions[concept_id]['lines'].append(line.id)
            else:
                perceptions[concept_id] = {
                    'base': base,
                    # 'amount': amount,
                    'lines': [line.id],
                    'reg_code': taxapps.reg_code,
                    'tax_app_id': taxapps,
                }

        return perceptions

    @api.returns('perception.tax.line')
    @api.model
    def compute(self, perception_data, invoice):
        # Chequeamos si la Percepcion tiene seteado un state_id, que coincida
        # con el state_id de la direccion de entrega del partner.
        # Sino no se realiza la Percepcion
        applicable = self._check_perception_applicable(invoice,
                                                       perception_data)
        if not applicable:
            return

        # Chequeamos las percepciones a aplicar que matchean
        # (esto corresponde a una percepcion pero que pueden
        # existir varios conceptos y/o actividades)
        perceptions = self._compute_base_perception(invoice, perception_data)

        # Creamos las lineas de percepcion
        new_perception_lines = self.env['perception.tax.line']
        for concept_id, vals in perceptions.iteritems():
            # print concept_id, perception_vals
            # Aplicamos la percepcion por Concepto
            taxapp = vals['tax_app_id']

            base, amount = taxapp.apply_perception(vals, perception_data)

            if amount == 0.0:
                continue

            vals['amount'] = amount
            vals['base'] = base

            # Creamos la percepcion.tax.line
            perception_line_vals = {
                'name': self.name,
                'concept_id': concept_id,
                'invoice_id': invoice.id,
                'account_id': self.tax_id.account_collected_id.id,
                'base': vals['base'],
                'amount': vals['amount'],
                'manual': False,  # La creamos por sistema
                'reg_code': vals['reg_code'],
                'tax_app_id': taxapp.id,
                'perception_id': self.id,
                'base_code_id': self.tax_id.base_code_id.id,
                'tax_code_id': self.tax_id.tax_code_id.id,
                'state_id': self.state_id and self.state_id.id or False,
                'partner_id': invoice.partner_id.id,
            }

            # Creamos la perception.tax.line correspondiente
            # Le pasamos manual=False para que se cree la account.invoice.tax
            # con manual=False
            new_perception_lines += self.env['perception.tax.line'].\
                with_context(manual=False).create(perception_line_vals)
        return new_perception_lines


class PerceptionVatTax(models.Model):
    _name = "perception.vat.tax"
    _description = "VAT Taxes for Perception Calculation"
    _rec_name = 'tax_id'

    tax_id = fields.Many2one('account.tax', 'VAT Tax', required=True)
    application_id = fields.Many2one(
        'perception.tax.application', 'Perception Tax Application',
        required=True)
    rate = fields.Float(
        'Rate',
        help="Rate from 1.0 to 0.0. This is the proportion of percent " +
        "applied to base amount of this tax.")


class PerceptionConcept(models.Model):
    _name = "perception.concept"
    _description = "Perception Concepts"

    name = fields.Char('Description', size=256, required=True)
    code = fields.Char('Code', size=32)
    type = fields.Selection([('vat', 'VAT'),
                            ('gross_income', 'Gross Income'),
                            ('profit', 'Profit'),
                            ('other', 'Other')], 'Type', required=True)
    no_subject = fields.Boolean('No Subject',
                                help="Check this if Perception should not " +
                                "be applied for this Concept")
    account_ids = fields.Many2many(
        'account.account', 'account_perception_concept_rel',
        'concept_id', 'account_id', 'Accounts')
    notes = fields.Text('Notes')


class PerceptionActivity(models.Model):
    _name = "perception.activity"
    _description = "Perception Gross Income Activity"

    name = fields.Char('Description', size=256, required=True)
    code = fields.Char('Code', size=32)
    type = fields.Selection([('vat', 'VAT'),
                            ('gross_income', 'Gross Income'),
                            ('profit', 'Profit'),
                            ('other', 'Other')], 'Type', required=True)
    notes = fields.Text('Notes')


class PerceptionTaxApplication(models.Model):
    _name = "perception.tax.application"

    name = fields.Char('Description', size=128)
    reg_code = fields.Integer('Reg. Code')
    concept_id = fields.Many2one('perception.concept', 'Concept')
    activity_id = fields.Many2one('perception.activity', 'Activity')
    # 'operation_id' = fields.many2one('perception.operation', 'Operation')
    perception_id = fields.Many2one('perception.perception')
    tax_allowance = fields.Float(  # Minimo No Imponible
        'Tax Allowance', digits=dp.get_precision('Account'),
        help="Perception will be calculated over this amount.")
    exclude_tax_allowance = fields.Boolean(
        'Exclude Tax Allowance', default=False,
        help="Check this if Tax Allowance should be excluded from " +
        "calculated Base")
    calculation_base = fields.Selection([
        ('amount_taxed', 'Invoice Net Taxed'),
        ('amount_no_taxed', 'Invoice Net Untaxed'),
        ('amount_total', 'Invoice Total'),
        ('amount_untaxed', 'Invoice Subtotal'),
        ('proportional_vat', 'Rate Proportional VAT')
        # Alicuota proporcional al IVA
    ], 'Calculation Base', required=True)
    # user_defined_base = fields.Text('User Defined Base Calculation')
    # Campo para el calculo en caso de proportional_vat
    vat_tax_ids = fields.One2many(
        'perception.vat.tax', 'application_id', 'VAT Taxes for Calculation')
    tax_minimum = fields.Float(
        'Tax Minimum', digits=dp.get_precision('Account'),
        help="Perception is performed when the amount thereof " +
        "exceeds this value.")  # Monto Minimo
    percent = fields.Float(
        'Percent', digits=dp.get_precision('Account'),
        help="Percent to Apply if the Partner is inscripted in the Tax")
    # 'scale_id' = fields.many2one('perception.scale', 'Scale'),
    type = fields.Selection([('vat', 'VAT'),
                            ('gross_income', 'Gross Income'),
                            ('profit', 'Profit')], 'Type', required=True)
    sit_iibb = fields.Many2one(comodel_name='iibb.situation',
                               string='Situation of IIBB')

    _sql_constraints = [
        ('concept_activity_uniq',
         'unique (concept_id, activity_id, perception_id)',
         'The tuple of Concept, Activity must be unique per Perception !'),
    ]

    @api.model
    def _compute_proportional_vat(self, tax_application, percent, line_vals):
        vat_tax = {}
        base = 0.0

        for t in tax_application.vat_tax_ids:
            vat_tax[t.tax_id.id] = t.rate

        for tax_id, vals in line_vals['vat_taxes'].iteritems():
            if tax_id in vat_tax:
                base += vals['base_amount'] * vat_tax[tax_id]

        amount = round(base * (percent / 100.0), 2)
        return amount

    @api.multi
    def compute_base(self, percent, line_vals):
        self.ensure_one()
        tax_application = self

        # TODO: De acuerdo al calculation_base,
        # llamamos a la funcion correspondiente
        if tax_application.calculation_base == 'proportional_vat':
            base = line_vals['amount_taxed']
        elif tax_application.calculation_base == 'amount_taxed':
            base = line_vals['amount_taxed']
        elif tax_application.calculation_base == 'amount_total':
            base = line_vals['amount_total']
        elif tax_application.calculation_base == 'amount_no_taxed':
            base = line_vals['amount_no_taxed']
        elif tax_application.calculation_base == 'amount_untaxed':
            base = line_vals['amount_untaxed']
        # elif tax_application.calculation_base == 'other':
        #     base = self._compute_user_defined_base(
        #         cr, uid, invoice, tax_application.user_defined_base, context)
        else:
            return 0.0, 0.0

        return base

    def apply_perception(self, vals, perception_data):
        percent = perception_data['percent']
        excluded_percent = perception_data['excluded_percent']

        # Si la alicuota que esta en la ficha del partner es negativa,
        # se toma la de la regla que se aplica.
        # Si es 0.0, se toma ese valor, 0.0.
        if percent < 0:
            percent = self.percent

        base = vals['base']
        if base < self.tax_allowance:
            return 0.0, 0.0

        if self.exclude_tax_allowance:
            base -= self.tax_allowance

        # TODO: Testear proportional_vat
        if self.calculation_base == 'proportional_vat':
            amount = self._compute_proportional_vat(percent, vals)
        else:
            amount = round(base * (percent / 100.0), 2)

        # Chequeamos contra el minimo a percibir
        if amount < self.tax_minimum:
            return 0.0, 0.0

        # Si la cantidad de la percepcion es 0.0, tambien lo sera
        # la base, para que de esta manera no se aplique percepcion
        if amount == 0.0:
            base = 0.0

        # Si tenemos excluded_percent, lo aplicamos
        amount *= (1 - excluded_percent)

        return base, amount
