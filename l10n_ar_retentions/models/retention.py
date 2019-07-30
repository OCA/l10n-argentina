##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta as relatived

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)


class FO:
    """
    Fake Object ( ͡º ͜ʖ ͡º)
    """
    id = False

    def address_get():
        return {}


class RetentionError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

    def __repr__(self):
        return self.__str__()


class retention_retention(models.Model):
    _name = "retention.retention"
    _inherit = "retention.retention"

    code = fields.Char('AFIP Code', required=False, size=32)
    general_resolution = fields.Char('GR Number', required=False, size=64)
    notes = fields.Text('Notes')
    vat_application_ids = fields.One2many(
        'retention.tax.application', 'retention_id', 'VAT Tax Application',
        domain=[('type', '=', 'vat')])
    profit_application_ids = fields.One2many(
        'retention.tax.application', 'retention_id', 'Profit Tax Application',
        domain=[('type', '=', 'profit')])
    gi_application_ids = fields.One2many(
        'retention.tax.application', 'retention_id',
        'Gross Income Tax Application', domain=[('type', '=', 'gross_income')])
    applicable_state = fields.Selection([
        ('dest', 'Destination'),
        ('source', 'Source'),
        ('always', 'Always')], 'Applicable State', default='dest',
        help="Indicates if this Perception is applicable when:\n"
        "* State/Province is equals to source address\n"
        "* State/Province is equals to destination address\n"
        "* Always")
    check_sit_iibb = fields.Boolean(
        'Check IIBB Situation', default=False,
        help="If checked, when IIBB situation is Multilateral, " +
        "this retention is always applicable")
    always_apply_padron = fields.Boolean(
        'Always Apply from Padron', default=False,
        help="If checked, when the partner has a perception exception " +
        "and it was generated from a padron, this perception will be applied")

    @api.model
    def _get_concepts_from_account(self, retention, account):
        concepts = account.retention_concept_ids.filtered(
            lambda c: c.type == retention.type)
        if not concepts:
            raise ValidationError(
                _("Retention Error\n") +
                _("Accont %s[%s] must have an associated concept for %s. " +
                  "Please configure it!") % (account.name, account.code,
                                             retention.name))
        return concepts

    @api.multi
    def check_applicable(
            self, sit_iibb=False, from_padron=False,
            source_shipping_id=FO(), destination_shipping_id=FO()):
        self.ensure_one()
        partner_model = self.env['res.partner']
        if not self.state_id:
            return True

        if self.applicable_state == 'always':
            return True

        if self.always_apply_padron and from_padron:
            return True

        # Chequeamos la situacion de IIBB, si es CM,
        # directamente retornamos True
        if self.check_sit_iibb:
            _logger.info("Chequeo de situacion IIBB activado")
            multilateral = self.env.ref(
                "l10n_ar_point_of_sale.iibb_situation_multilateral")
            if sit_iibb == multilateral:
                _logger.info("Partner es Convenio Multilateral, " +
                             "aplica Retencion %s", self.name)
                return True

        partner_state = False
        retention_state = self.state_id.id

        if self.applicable_state == 'dest':
            partner_state = partner_model.browse(
                destination_shipping_id.address_get(
                    ['delivery']).get('delivery')).id

            if not partner_state:
                raise RetentionError(
                    _('There is no State/Province configured for ' +
                      'the Supplier while computing Retention: %s') %
                    (self.name))

        elif self.applicable_state == 'source':
            user = self.env.user
            partner = user.company_id.partner_id
            partner_state = partner_model.browse(
                source_shipping_id.address_get(
                    ['delivery']).get('delivery') or
                partner.address_get(['delivery']).get(
                    'delivery')).id

            if not partner_state:
                raise RetentionError(
                    _('There is no State/Province configured for ' +
                      'this Company'))

        # Hacemos el chequeo de los states
        return retention_state == partner_state

    def _parse_move_lines(self, move):
        not_payable_moves = move.line_ids.filtered(
            lambda ml: ml.account_id.internal_type != 'payable')
        tax_mls = not_payable_moves.filtered(
            lambda ml: ml.tax_line_id)
        taxed_mls = not_payable_moves.filtered(
            lambda ml: ml.tax_ids)
        untaxed_mls = not_payable_moves.filtered(
            lambda ml: not (ml.tax_line_id + ml.tax_ids))

        amount_tax = sum([ml.credit or ml.debit for ml in tax_mls])
        amount_untaxed = sum([ml.credit or ml.debit for ml in taxed_mls])
        amount_no_taxed = sum([ml.credit or ml.debit for ml in untaxed_mls])
        amount_total = sum([ml.credit or ml.debit for ml in not_payable_moves])

        tax_lines = {
            at: tax_mls.filtered(lambda ml: ml.tax_line_id == at) for at
            in [at for at in tax_mls.mapped('tax_line_id')]
        }
        concept_lines = {
            at: taxed_mls.filtered(lambda ml: at in ml.tax_ids) for at
            in [at for at in taxed_mls.mapped('tax_ids')]
        }

        result = {
            'amount_untaxed': amount_untaxed,
            'amount_tax': amount_tax,
            'amount_no_taxed': amount_no_taxed,
            'amount_total': amount_total,
            'concept_lines': concept_lines,
            'tax_lines': tax_lines,
        }
        return result

    def _compute_base_retention(
            self, move_line, factor_to_pay, factor_unrec, prev_ret_ids,
            line_type, sit_iibb, logging_messages=[], activity=FO()):
        tax_app_obj = self.env['retention.tax.application']
        retention = self

        # Por cada linea, nos fijamos la configuracion del producto
        retentions = {}

        move = move_line.move_id
        parsed_move = self._parse_move_lines(move)

        # Obtenemos el concepto desde la cuenta contable
        logging_messages.append("Parseando lineas del asiento: %s [%s]" %
                                (move.name, move.ref))
        for tax_id, mls in parsed_move['concept_lines'].items():
            for ml in mls:

                # Evitamos la linea de la deuda
                concepts = self._get_concepts_from_account(
                    retention, ml.account_id)

                logging_messages.append("Linea: %s [%s]" %
                                        (ml.name, ml.account_id.name))

                # Si el concepto no esta sujeto a retencion, continuamos
                no_subject = False
                for concept in concepts:
                    if concept and concept.no_subject:
                        logging_messages.append(
                            "Concepto no sujeto a Retencion: %s" %
                            concept.name)
                        no_subject = True

                if no_subject:
                    continue

                concept_name = (" ").join([c.name for c in concepts])
                activity_name = activity and activity.name or ''

                # Buscamos las taxapps que concuerden
                tapp_domain = [
                    ('retention_id', '=', retention.id),
                    ('concept_id', 'in', concepts.ids),
                    ('activity_id', '=', activity and activity.id)]
                iibb_domain = []
                if retention.type == 'gross_income':
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
                        _("Retention Error!\n") +
                        _("There is no configured a Retention Application " +
                          "(%s) that corresponds to\nActivity: %s \n" +
                          "Concept: %s\n for the Account %s") % (
                              retention.name, activity_name, concept_name,
                              ml.account_id.name))

                if len(taxapps) > 1:
                    raise ValidationError(
                        _("Retention Error!\n") +
                        _("There is more than one Retention Application " +
                          "(%s) configured that corresponds to\n" +
                          "Activity: %s \nConcept: %s\n for the Account %s") %
                        (retention.name, activity_name, concept_name,
                         ml.account_id.name))

                # Si ya retuvimos y esta calculado sobre
                # el montos de la factura, continuamos,
                # pero si esta calculado sobre el monto del pago
                # no retornamos porque se retiene sobre lo que se va pagando
                # asi que tenemos que tener en cuenta
                # facturas con pagos parciales
                taxapp = taxapps
                logging_messages.append(
                    "Tax Application: [id: %s ; reg_code: %s] %s" %
                    (taxapp.id, taxapp.reg_code, taxapp.concept_id.name))
                if taxapp.calculation_base not in [
                        'payment_amount', 'payment_amount_untaxed'] \
                        and len(prev_ret_ids):
                    continue

                # Obtenemos toda la info contable de la linea de factura
                # todas las cantidades y los impuestos de IVA aplicados
                # OJO: Solo los de IVA y de cada linea en particular.
                # Esto no nos trae
                # ninguna informacion con respecto a Percepciones

                # Hacemos el computo de la Retencion por linea de factura
                base = ml.credit or ml.debit
                logging_messages.append("Base tomada: %f" % (base))
                if line_type == 'income':
                    base *= -1

                # Luego vamos agrupando por Concepto y
                # Factura (no por actividad)
                # TODO: Deberiamos tener alguna configuracion
                # para agrupar o no por factura tambien
                invoice = ml.invoice_id or False

                concept = taxapp.concept_id
                if taxapp.calculation_base in [
                        'payment_amount', 'payment_amount_untaxed']:
                    key = (concept, False)
                else:
                    key = (concept, invoice)

                base_to_pay = round(base / factor_to_pay, 2)
                base_unrec = round(base / factor_unrec, 2)
                retentions.setdefault(key, {
                    'base': 0.0,
                    'base_to_pay': 0.0,
                    'base_unrec': 0.0,
                    'taxapp': taxapp,
                    'lines': self.env['account.move.line'],
                })
                retentions[key]['base'] += base
                retentions[key]['base_to_pay'] += base_to_pay
                retentions[key]['base_unrec'] += base_unrec
                retentions[key]['lines'] += ml
                logging_messages.append(
                    ("Agregando a la key %s ==> Base: %f Base " +
                     "To Pay: %f Base Unrec: %f") %
                    (key, base, base_to_pay, base_unrec))

                logging_messages.append(
                    ("Subtotales %s ==> Base: %f Base To Pay: " +
                     "%f Base Unrec: %f") %
                    (key, retentions[key]['base'],
                     retentions[key]['base_to_pay'],
                     retentions[key]['base_unrec']))

        # Mensajes de logging
        _logger.debug("\n\nLogging messages: ")
        for msg in logging_messages:
            _logger.debug(msg)
        return retentions


class RetentionVatTax(models.Model):
    _name = "retention.vat.tax"
    _description = "VAT Taxes for Retention Calculation"
    _rec_name = 'tax_id'

    tax_id = fields.Many2one('account.tax', 'VAT Tax', required=True)
    application_id = fields.Many2one('retention.tax.application',
                                     'Application', required=True)
    rate = fields.Float(
        'Rate',
        help="Rate from 1.0 to 0.0. This is the proportion of percent " +
        "applied to base amount of this tax.")


class RetentionScale(models.Model):
    _name = "retention.scale"
    _description = "Scale for Retention Calculation"

    name = fields.Char('Name', required=True, size=64)
    line_ids = fields.One2many('retention.scale.line', 'scale_id',
                               'Scale Lines')


class RetentionScaleLine(models.Model):
    _name = "retention.scale.line"
    _description = "Scale Line for Retention Calculation"

    name = fields.Char('Name', required=True, size=64)
    limit = fields.Float('Limit', required=True)
    percent = fields.Float('Percent', required=True)
    scale_id = fields.Many2one('retention.scale', 'Scale', required=True)


class RetentionConcept(models.Model):
    _name = "retention.concept"
    _description = "Retention Profit Concepts"

    name = fields.Char('Description', size=256, required=True)
    code = fields.Char('Code', size=32)
    type = fields.Selection([('vat', 'VAT'),
                             ('gross_income', 'Gross Income'),
                             ('profit', 'Profit'),
                             ('other', 'Other')], 'Type', required=True)
    no_subject = fields.Boolean(
        'No Subject',
        help="Check this if Retention should not be applied for this Concept")
    account_ids = fields.Many2many(
        comodel_name='account.account',
        relation='account_retention_concept_rel',
        column1='concept_id', column2='account_id',
        string='Accounts')
    notes = fields.Text('Notes')


class AccountAccount(models.Model):
    _name = 'account.account'
    _inherit = 'account.account'

    retention_concept_ids = fields.Many2many(
        comodel_name='retention.concept',
        relation='account_retention_concept_rel',
        column1='account_id', column2='concept_id',
        string='Concepts')


class RetentionActivity(models.Model):
    _name = "retention.activity"
    _description = "Retention Gross Income Activity"

    name = fields.Char('Description', size=256, required=True)
    code = fields.Char('Code', size=32)
    type = fields.Selection([('vat', 'VAT'),
                             ('gross_income', 'Gross Income'),
                             ('profit', 'Profit'),
                             ('other', 'Other')], 'Type', required=True)
    notes = fields.Text('Notes')


class RetentionTaxApplication(models.Model):
    _name = "retention.tax.application"

    name = fields.Char('Description', size=128)
    reg_code = fields.Integer('Reg. Code')
    concept_id = fields.Many2one('retention.concept', 'Concept')
    activity_id = fields.Many2one('retention.activity', 'Activity')
    retention_id = fields.Many2one('retention.retention')
    # Minimo No Imponible
    tax_allowance = fields.Float(
        'Tax Allowance', digits=dp.get_precision('Account'),
        help="Retention will be calculated over this amount.")
    exclude_tax_allowance = fields.Boolean(
        'Exclude Tax Allowance', default=False,
        help="Check this if Tax Allowance should be excluded " +
        "from calculated Base")
    calculation_base = fields.Selection([
        ('amount_untaxed', 'Invoice Subtotal'),
        # Alicuota proporcional al IVA
        ('proportional_vat', 'Rate Proportional VAT'),
        ('payment_amount_untaxed', 'Payment Amount Untaxed'),
        # ('amount_taxed', 'Invoice Net Taxed'),
        # ('amount_no_taxed', 'Invoice Net Untaxed'),
        # ('amount_total', 'Invoice Total'),
        # ('payment_amount', 'Payment Amount'),
    ], 'Calculation Base', required=True)
    vat_tax_ids = fields.One2many(
        'retention.vat.tax', 'application_id', 'VAT Taxes for Calculation')
    # Monto Minimo
    tax_minimum = fields.Float(
        'Tax Minimum', digits=dp.get_precision('Account'),
        help="Retention is performed when the amount thereof " +
        "exceeds this value.")
    aliq_type = fields.Selection([
        ('percent', 'Percent'),
        ('scale', 'Scale')], 'Aliquot Type', required=True)
    percent = fields.Float(
        'Percent', digits=dp.get_precision('Account'),
        help="Percent to Apply if the Partner is inscripted in the Tax")
    scale_id = fields.Many2one('retention.scale', 'Scale')
    type = fields.Selection([('vat', 'VAT'),
                             ('gross_income', 'Gross Income'),
                             ('profit', 'Profit')], 'Type', required=True)
    sit_iibb = fields.Selection([
        ('1', 'Local'),
        ('2', 'Convenio Multilateral'),
        ('4', 'No Inscripto'),
        ('5', 'Regimen Simplificado')], 'Situation of IIBB')

    _sql_constraints = [
        ('concept_activity_uniq',
         'unique (concept_id, activity_id, retention_id)',
         'The tuple of Concept, Activity must be unique per Retention !'),
    ]

    @api.multi
    def _compute_proportional_vat(self, percent, line_vals):
        vat_tax = {}
        base = 0.0

        for t in self.vat_tax_ids:
            vat_tax[t.tax_id.id] = t.rate

        for tax_id, vals in line_vals['vat_taxes'].iteritems():
            if tax_id in vat_tax:
                base += vals['base_amount'] * vat_tax[tax_id]

        amount = round(base * (percent / 100.0), 2)
        return amount

    def _compute_amount_via_scale(self, base):

        amount = 0.0
        prev_limit = 0.0

        for sc in self.scale_id.line_ids:
            range_limit = sc.limit - prev_limit
            b = base - sc.limit

            if b < 0 or sc.limit == -1:
                b = base - prev_limit
                amount += round(b * (sc.percent / 100.0), 2)
                return amount
            else:
                amount += round((range_limit) * (sc.percent / 100.0), 2)

            prev_limit = sc.limit

        return amount

    @api.multi
    def _get_month_date_span_from_date(self, date=False):
        if not date:
            date = fields.Date.context_today(self)

        # Obtenemos las fechas de mes calendario
        # al que corresponde este voucher

        dt = datetime.strptime(date, DSDF)
        date_start = (dt + relatived(day=1)).strftime(DSDF)
        date_finish = (dt + relatived(day=31)).strftime(DSDF)
        return date_start, date_finish

    @api.multi
    def get_period_partner_payments(self, partner, concept,
                                    po_date=False):
        date_start, date_finish = self._get_month_date_span_from_date(po_date)
        payment_order_model = self.env['account.payment.order']
        payment_order_line_model = self.env['account.payment.order.line']
        prev_pos = payment_order_model.search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'posted'),
            ('date', '>=', date_start),
            ('date', '<=', date_finish)])
        debt_moves = prev_pos.mapped('debt_line_ids.move_line_id.move_id')
        debt_untax_mls = debt_moves.mapped('line_ids').filtered(
            lambda ml: ml.account_id in concept.account_ids and
            ml.tax_ids and not ml.tax_line_id)
        income_moves = prev_pos.mapped('income_line_ids.move_line_id.move_id')
        income_untax_mls = income_moves.mapped('line_ids').filtered(
            lambda ml: ml.account_id in concept.account_ids and
            ml.tax_ids and not ml.tax_line_id)
        # Use the proportional amount of line being paid, searching in
        # the old apo's and gathering the apol related to the untaxed ones
        debt_untax_mls_ok = []
        for ml in debt_untax_mls:
            amls_w_tax = ml.move_id.mapped('line_ids').filtered(
                lambda ml: ml.account_id.internal_type in ['payable'])
            domain = [
                ('payment_order_id', 'in', prev_pos.ids),
                ('move_line_id', 'in', amls_w_tax.ids),
            ]
            pol_todo = payment_order_line_model.search(domain)
            amount = (ml.credit or ml.debit)
            factor = 0.0
            for pol in pol_todo:
                factor += pol.amount / pol.amount_original

            if factor:
                amount = amount * round(factor, 3)
#            if pol_todo:
#                factor = pol_todo.amount / pol_todo.amount_original
#                amount = amount * factor
            debt_untax_mls_ok.append(amount)
        # Use the proportional amount of line being paid, searching in
        # the old apo's and gathering the apol related to the untaxed ones
        income_untax_mls_ok = []
        for ml in income_untax_mls:
            amls_w_tax = ml.move_id.mapped('line_ids').filtered(
                lambda ml: ml.account_id.internal_type in ['payable'])
            domain = [
                ('payment_order_id', 'in', prev_pos.ids),
                ('move_line_id', 'in', amls_w_tax.ids),
            ]
            pol_todo = payment_order_line_model.search(domain)
            amount = (ml.credit or ml.debit)
            factor = 0.0
            for pol in pol_todo:
                factor += pol.amount / pol.amount_original

            if factor:
                amount = amount * round(factor, 3)
            income_untax_mls_ok.append(amount)
        untaxed_debt = sum(debt_untax_mls_ok)
        untaxed_inc = sum(income_untax_mls_ok)
        untaxed_amount = untaxed_debt - untaxed_inc
        untaxed_amount += self.get_period_partner_advance_payments(prev_pos)
        return untaxed_amount

    @api.multi
    def get_period_partner_advance_payments(self, prev_pos):
        extra_untaxed_amount = 0.0
        for po in prev_pos:
            if any(po.debt_line_ids.mapped('amount') +
                   po.income_line_ids.mapped('amount')) or not po.amount \
                   or not po.retention_ids:
                continue
            extra_untaxed_amount += po.amount - sum(
                po.retention_ids.mapped('amount'))
        return extra_untaxed_amount

    def get_period_base_amount(self, partner, concept,
                               po_date=False):
        retention_line_model = self.env['retention.tax.line']

        date_start, date_finish = self._get_month_date_span_from_date(po_date)

        # Buscamos las retenciones
        domain = [
            ('partner_id', '=', partner.id),
            ('retention_id.type', '=', 'profit'),
            ('concept_id', '=', concept.id),
            ('date', '>=', date_start),
            ('date', '<=', date_finish),
            ('payment_order_id.state', 'in', ['posted']),
        ]

        ret_lines = retention_line_model.search(
            domain, order="date desc, id desc")

        base = sum([ret.base for ret in ret_lines])
        amount = sum([ret.amount for ret in ret_lines])
        return base, amount

    def apply_retention(self, partner, percent, excluded_percent,
                        vals, po_date):
        # Si la alicuota que esta en la ficha del partner es negativa,
        # se toma la de la regla que se aplica.
        # Si es 0.0, se toma ese valor, 0.0.
        if percent < 0:
            percent = self.percent

        # Aca tenemos que ver que si es un calculo de ganancias hay que
        # chequear el tema de varios pagos en un mes al mismo beneficiario
        period_base = 0.0
        period_amount = 0.0
        period_payment_amount = 0.0
        base = vals['base']
        to_pay = vals['to_pay']
        if self.calculation_base in [
                'payment_amount', 'payment_amount_untaxed']:
            base = to_pay

        if self.retention_id.type == 'profit':
            period_base, period_amount = self.get_period_base_amount(
                partner, self.concept_id, po_date)
            period_payment_amount = self.get_period_partner_payments(
                partner, self.concept_id, po_date)

            # Si tenemos pagos anteriores de este concepto,
            # los sumamos a la base y al ser de ganancias,
            # tenemos que usar la cantidad a pagar neto de Impuestos
            base = to_pay + period_payment_amount

        # Puede darse el caso en que FAC-NC quede en 0.0 y
        # realizaba una division por cero
        if round(base, 2) == 0.0:
            return 0.0, 0.0

        # Agregamos el signo de la base si es que viene de una NC
        sign_base = base / abs(base)
        base = abs(base)

        if base < self.tax_allowance:
            return 0.0, 0.0

        if self.exclude_tax_allowance:
            base -= self.tax_allowance

        if self.calculation_base == 'proportional_vat':
            # TODO: Chequear que esta funcion funcione correctamente
            amount = self._compute_proportional_vat(percent, base)
        else:
            if self.aliq_type == 'percent':
                amount = round(base * (percent / 100.0), 2)
            else:
                amount = self._compute_amount_via_scale(base)

        # Si es de ganancias, le detraemos las retenciones de ganancias
        # ya practicadas para este concepto
        # en el mes calendario en pagos previos a este proveedor
        if self.retention_id.type == 'profit':
            amount -= period_amount

        # Chequeamos contra el minimo a percibir
        if amount < self.tax_minimum:
            return 0.0, 0.0

        # Chequeamos que la cantidad a retener no sea negativa
        if amount < 0:
            raise ValidationError(
                _('Retention Error!\n') +
                _('There is an error in retention configuration because ' +
                  'amount of %s is negative') % self.retention_id.name)
        elif amount == 0.0:
            return 0.0, 0.0

        # Aplicamos el porcentaje de eximision si es que lo hay
        amount *= (1 - excluded_percent)

        return base*sign_base, amount*sign_base
