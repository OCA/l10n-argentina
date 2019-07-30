##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

import logging
from pprint import pformat as pf

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

_logger = logging.getLogger()


class RetentionTaxLine(models.Model):
    _name = "retention.tax.line"
    _inherit = "retention.tax.line"

    move_line_ids = fields.Many2many(
        'account.move.line', 'retention_tax_line_move_line_rel',
        'retention_line_id', 'move_line_id', 'Move Lines')
    invoice_id = fields.Many2one('account.invoice', 'Invoice')
    invoice_ref = fields.Char('Invoice Reference', size=64)
    concept_id = fields.Many2one('retention.concept', 'Concept')
    taxapp_id = fields.Many2one(
        'retention.tax.application', 'Tax Application')
    reg_code = fields.Integer('Reg. Code')
    date_applied = fields.Date(
        'Date Applied',
        help="This is the date of the real application of the retention")
    manual = fields.Boolean('Manual', default=True)
    excluded_percent = fields.Float('Percentage of exclusion')
    exclusion_date_certificate = fields.Date(
        'Exclusion General Resolution Date')
    unlinkable = fields.Boolean('Unlinkable', default=True)

    @api.onchange('retention_id')
    def onchange_retention_id(self):
        res = {}
        if self.retention_id:
            res['domain'] = {
                'concept_id': [('type', '=', self.retention_id.type)],
            }
        return res

    @api.model
    def get_readeable_name(self):
        """
        Returns an easy name used for exporters to print error messages
        """
        rtl_id = self.id
        rtl_name = self.name
        rtl_partner_name = self.partner_id.name or 'Undefined'
        name = u"RTL(#{0})[{1}-{2}]".format(rtl_id, rtl_name, rtl_partner_name)
        return name


class AccountPaymentOrder(models.Model):
    _name = 'account.payment.order'
    _inherit = 'account.payment.order'

    date_effective = fields.Date(
        'Effective Date',
        help="This is the effective date when one give this voucher " +
        "to the Supplier")
    receipt_number = fields.Char(
        'Supplier Receipt Number', size=32,
        help="This is the number of the receipt given by the Supplier")
    disable_retentions = fields.Boolean(
        'Disable Retentions',
        help="Check this if you want to disable automatic " +
        "calculation of retention on this payment")

    @api.multi
    def payment_order_amount_hook(self):
        amount = super().payment_order_amount_hook()
        if any(self.debt_line_ids.mapped('amount') +
               self.income_line_ids.mapped('amount')) or not amount or \
                self.disable_retentions:
            return amount
        amount += self.compute_advance_payment_retentions(amount)
        return amount

    @api.multi
    def compute_advance_payment_retentions(self, amount):
        amount = amount - sum(self.retention_ids.mapped('amount'))
        new_ret_amount = 0.0
        if not amount:
            self.retention_ids = False
            return amount
        tax_app_obj = self.env['retention.tax.application']
        partner_retentions = self.partner_id._get_retentions_to_apply(
            self.date)
        create_vals = []
        for advance_ret in self.partner_id.advance_retention_ids:
            if (advance_ret.retention_id, advance_ret.concept_id) in \
                    [(rtl.retention_id, rtl.concept_id) for
                     rtl in self.retention_ids]:
                continue
            ret_vals = partner_retentions.get(advance_ret.retention_id.id)
            if not ret_vals:
                raise ValidationError(
                    _("Retention %s is not configured for Partner " +
                      "Fiscal Position %s") % (
                          advance_ret.retention_id.name,
                          self.partner_id.account_fiscal_position_id.name))
            tapp_domain = [
                ('retention_id', '=', advance_ret.retention_id.id),
                ('concept_id', '=', advance_ret.concept_id.id)]
            taxapp = tax_app_obj.search(tapp_domain)
            if not taxapp:
                raise ValidationError(
                    _("Retention Error!\n") +
                    _("There is no configured a Retention Application " +
                      "(%s) that corresponds to Concept: %s") % (
                          advance_ret.retention_id.name,
                          advance_ret.concept_id.name))

            if len(taxapp) > 1:
                raise ValidationError(
                    _("Retention Error!\n") +
                    _("There is more than one Retention Application " +
                      "(%s) configured that corresponds to " +
                      "Concept: %s") %
                    (advance_ret.retention_id.name,
                     advance_ret.concept_id.name))
            vals = {
                'base': amount,
                'to_pay': amount,
            }
            base, amount = taxapp.apply_retention(
                    self.partner_id, ret_vals.get('percent'),
                    ret_vals.get('excluded_percent'), vals, self.date)
            if not amount:
                continue
            retention_line_vals = self._prepare_advanced_payment_retention(
                advance_ret, taxapp, ret_vals, base, amount)
            create_vals.append(retention_line_vals)
            new_ret_amount += amount
            _logger.info("Retentions to create: %s" % pf(retention_line_vals))
        if create_vals:
            self.retention_ids = [(0, 0, val) for val in create_vals]
        return new_ret_amount

    @api.multi
    def _prepare_advanced_payment_retention(
            self, advance_ret, taxapp, ret_vals, base, amount):
        retention_line_vals = {
            'name': advance_ret.retention_id.name,
            'concept_id': advance_ret.concept_id.id,
            'date': self.date,
            'account_id': advance_ret.retention_id.tax_id.account_id.id,
            'base': base,
            'amount': amount,
            'manual': False,
            'retention_id': advance_ret.retention_id.id,
            'certificate_no': '',
            'taxapp_id': taxapp.id,
            'reg_code': taxapp.reg_code,
            'state_id': advance_ret.retention_id.state_id.id,
            'excluded_percent': ret_vals.get('excluded_percent'),
            'exclusion_date_certificate': ret_vals.get(
                'exclusion_date_certificate'),
        }
        return retention_line_vals

    @api.multi
    def recompute_voucher_lines(self, partner_id, journal_id, price,
                                currency_id, ttype, date):
        res = super(AccountPaymentOrder, self).recompute_voucher_lines(
            partner_id, journal_id, price, currency_id, ttype, date)

        # Si es un pago, quitamos todo el calculo de imputacion automatica
        # porque interfiere en el calculo de retenciones automaticas
        if ttype == 'payment' and not self._context.get('immediate_payment'):
            all_l = res['value']['line_cr_ids'] + res['value']['line_dr_ids']
            for line in all_l:
                line['amount'] = 0.0
                line['reconcile'] = False

        return res

    @api.multi
    def calculate_retentions(self):
        self.ensure_one()
        retentions = {}
        # Computamos todas las retenciones para el voucher
        partner_retentions = self.partner_id._get_retentions_to_apply(
            self.date)

        for partner_ret in list(partner_retentions.values()):
            excluded_percent = partner_ret.get('excluded_percent')
            if excluded_percent == 1.0:
                continue

            ret = partner_ret.get('retention')
            res = self.calculate_single_retention(partner_ret)

            # Generamos la key
            for ret in res:
                key = (ret['retention_id'], ret['concept_id'],
                       ret['invoice_ref'])
                if key not in retentions:
                    retentions[key] = ret
                else:
                    raise Warning(
                        _('Something is wrong with retention calculation ' +
                          'because there are more than one tuple (voucher ' +
                          'line, retention, concept) applied to this voucher'))

        return list(retentions.values())

    @api.multi
    def calculate_single_retention(self, retention_data):
        self.ensure_one()
        partner_model = self.env['res.partner']
        retention = retention_data.get('retention')
        activity = retention_data.get('activity_id')
        percent = retention_data.get('percent')
        excluded_percent = retention_data.get('excluded_percent')
        exclusion_date_certificate = retention_data.get(
            'exclusion_date_certificate')
        sit_iibb = retention_data.get('sit_iibb')
        from_padron = retention_data.get('from_padron')

        res = []

        logging_messages = []
        all_concepts = {}

        logging_messages.append("\n\nAplicando %s ==>" % (self.name))
        logging_messages.append(
            ("Actividad: %s Porcentaje en partner: %f. " +
             "Porcentaje de Exclusion: %f") % (
                activity, percent, excluded_percent))
        for po_line in [
                line for line in (self.income_line_ids + self.debt_line_ids)
                if line.amount]:
            # Chequeamos si la Retencion tiene seteado un state_id,
            # que coincida con el state_id de la direccion de
            # entrega del partner. Sino no se realiza # la Retencion
            invoice = po_line.move_invoice_id
            destination_shipping = invoice.address_shipping_id or \
                partner_model.browse(
                    invoice.partner_id.address_get(['delivery']).get(
                        'delivery'))
            source_shipping = self.env.user.company_id.partner_id
            applicable = retention.check_applicable(
                sit_iibb=sit_iibb, from_padron=from_padron,
                source_shipping_id=source_shipping,
                destination_shipping_id=destination_shipping)
            if not applicable:
                continue

            move_line = po_line.move_line_id

            # Chequeamos si la factura que corresponde a esta move_line ya
            # tiene una retencion aplicada previa de este tipo en algun pago
            # parcial previo.
            # Por lo tanto, no corresponde retener nuevamente porque sino
            # estariamos aplicando dos veces la misma
            # retencion sobre el pago de una misma factura
            prev_ret_ids = self._check_previous_retentions(
                retention, move_line)

            # Agrupamos por retencion y concepto antes de aplicar la retencion
            # O sea, vamos a calcular las bases para cada
            # (retencion,concepto) y luego aplicamos la retencion

            # Obtenemos el factor desde el total de la deuda contra
            # lo que se pretende pagar
            mla = (move_line.credit or move_line.debit)
            factor_to_pay = mla / po_line.amount
            factor_unrec = mla / po_line.amount_unreconciled

            logging_messages.append("Linea a aplicar %s" % (po_line.ref))

            retentions = retention._compute_base_retention(
                move_line, factor_to_pay,
                factor_unrec, prev_ret_ids, po_line.type, sit_iibb,
                activity=activity, logging_messages=logging_messages)

            for (concept, invoice), vals in retentions.items():
                # Agrupamos por concepto y factura
                key = (retention.id, concept, invoice)
                all_concepts.setdefault(key, {
                    'base': 0.0,
                    'to_pay': 0.0,
                    'taxapp': vals['taxapp'],
                    'move_lines': self.env['account.move.line'],
                })
                all_concepts[key]['base'] += vals['base_unrec']
                all_concepts[key]['to_pay'] += vals['base_to_pay']

                # Agregamos la move_line.
                # En realidad nos interesa la voucher_line,
                # pero a estas alturas todavia no la tenemos
                if move_line not in all_concepts[key]['move_lines']:
                    all_concepts[key]['move_lines'] += move_line

        # Ahora que tenemos las bases agrupadas por concepto
        # aplicamos el calculo de la retencion
        for (ret, concept, invoice), vals in all_concepts.items():
            taxapp = vals['taxapp']
            base, amount = taxapp.apply_retention(
                    move_line.partner_id, percent,
                    excluded_percent, vals, self.date)
            all_concepts[key]['amount'] = amount

            if amount == 0.0:
                continue

            # Creamos las lineas de retencion
            # Creamos la retention.tax.line
            retention_line_vals = {
                'name': retention.name,
                'move_line_ids': [(6, 0, all_concepts[key]['move_lines'].ids)],
                'concept_id': concept.id,
                'invoice_id': invoice and invoice.id,
                'invoice_ref': invoice and invoice.name_get()[0][1],
                'date': self.date,
                'account_id': retention.tax_id.account_id.id,
                'base': base,
                'amount': amount,
                'manual': False,  # La creamos por sistema
                'retention_id': retention.id,
                'certificate_no': '',
                'taxapp_id': taxapp.id,
                'reg_code': taxapp.reg_code,
                'state_id': retention.state_id.id,
                'excluded_percent': excluded_percent,
                'exclusion_date_certificate': exclusion_date_certificate,
            }

            res.append(retention_line_vals)

        return res

    def _check_previous_retentions(self, retention, move_line=False):
        sql = """
        SELECT rtl.id FROM retention_retention r
        JOIN retention_tax_line rtl ON r.id=rtl.retention_id
        JOIN retention_tax_line_move_line_rel rv ON rv.retention_line_id=rtl.id
        JOIN account_move_line ml ON ml.id=rv.move_line_id
        JOIN account_payment_order po ON po.id=rtl.payment_order_id
        JOIN account_payment_order_line pol
            ON pol.move_line_id=ml.id
            AND pol.payment_order_id=po.id
        JOIN account_move mv ON mv.id=ml.move_id
        WHERE r.id=%(ret_id)s AND po.state='posted'
        """

        q_params = {
            'ret_id': retention.id,
        }
        if move_line:
            q_params['move_line_id'] = move_line.id
            sql += " AND ml.id=%(move_line_id)s"

        self.env.cr.execute(sql, q_params)
        res = self.env.cr.fetchall()

        line_ids = [r[0] for r in res]
        return line_ids

    @api.model
    def _compute_writeoff_amount(self, line_dr_ids, line_cr_ids,
                                 amount, ttype):
        debit = credit = 0.0
        sign = ttype == 'payment' and -1 or 1

        for l in line_dr_ids:
            if isinstance(l, dict):
                debit += l['amount']
            elif isinstance(l, models.Model):
                debit += l.amount
        for l in line_cr_ids:
            if isinstance(l, dict):
                credit += l['amount']
            elif isinstance(l, models.Model):
                credit += l.amount
        return amount - sign * (credit - debit)

    @api.onchange('income_line_ids', 'debt_line_ids',
                  'disable_retentions', 'date')
    def onchange_lines(self):
        for po in self:
            if po.type != 'payment':
                return
            if po.disable_retentions:
                po.retention_ids = False
                continue
            if any(self.debt_line_ids.mapped('amount') +
                   self.income_line_ids.mapped('amount')):
                vals = po.calculate_retentions()

                _logger.info("Retentions to create: %s" % pf(vals))
                po.retention_ids = [(0, 0, val) for val in vals]
            else:
                if not po.amount:
                    po.retention_ids = False
                    continue
                po.compute_advance_payment_retentions(po.amount)

    @api.multi
    def proforma_voucher(self):
        for voucher in self:
            voucher.retention_ids.write({
                'unlinkable': False,
            })
        res = super(AccountPaymentOrder, self).proforma_voucher()
        return res

    @api.multi
    def unlink(self):
        self._check_retentions_unlinkable()
        return super(AccountPaymentOrder, self).unlink()

    @api.multi
    def action_cancel_draft(self):
        self._check_retentions_unlinkable()
        return super(AccountPaymentOrder, self).action_cancel_draft()

    @api.multi
    def _check_retentions_unlinkable(self):
        for voucher in self:
            u_rets = voucher.retention_ids.filtered(lambda x: not x.unlinkable)
            if u_rets:
                raise ValidationError(
                    _("Error!\n") +
                    _("Voucher %s [id: %s] has Unlinkable Retentions:\n" +
                      "%s") % (
                          voucher.name, voucher.id,
                          ("\n").join(["%s [id: %s]" % (r.name, r.id) for r
                                       in u_rets])))
        return True
