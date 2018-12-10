###############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (Martín Nicolás Cuesta)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

import logging
from pprint import pformat as pf

from openerp import models, fields, api
from openerp.exceptions import except_orm
from openerp.tools.translate import _

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
    taxapp_id = fields.Many2one('retention.tax.application',
                                'Tax Application')
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

    # @api.onchange('amount')
    # def onchange_amount_ret(self):
    #     """
    #     Besides original onchange,
    #     this one do not call recompute_voucher_lines
    #     """
    #     if self._context.get('immediate_payment'):
    #         rvl_res = self.recompute_voucher_lines(
    #             self.partner_id.id, self.journal_id.id,
    #             self.amount, self.currency_id.id,
    #             self._context['type'], self.date)
    #         self.line_dr_ids = rvl_res['value']['line_dr_ids']
    #         self.line_cr_ids = rvl_res['value']['line_cr_ids']
    #
    #     self.onchange_amount_payment()
    #
    #     self.writeoff_amount = self._compute_writeoff_amount(
    #         self.line_dr_ids, self.line_cr_ids, self.amount, self.type)
    #
    #     vals = self.onchange_rate(
    #         self.payment_rate, self.amount, self.currency_id.id,
    #         self.payment_rate_currency_id.id, self.company_id.id)
    #
    #     self.currency_help_label = 'currency_help_label' in vals['value'] \
    #         and vals['value']['currency_help_label'] or ''
    #     paicc = 'paid_amount_in_company_currency' in vals['value'] and \
    #         vals['value']['paid_amount_in_company_currency'] or 0.0
    #     self.paid_amount_in_company_currency = paicc
    #     return

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

    # def create_move_line_hook(self, move_id, move_lines):
    #     sequence_obj = self.env['ir.sequence']
    #     move_lines = super(AccountPaymentOrder, self).create_move_line_hook(
    #         move_id, move_lines)
    #
    #     # Asignamos los numeros de certificados a las retenciones
    #     # Si es de tipo payment. Porque si es un cobro, no deberiamos ponerle
    #     # nros de certificado nosotros
    #     if self.type == 'payment':
    #         groups = {}
    #         for ret in self.retention_ids:
    #             key = (ret.retention_id.id, ret.concept_id.id)
    #
    #             if key in groups:
    #                 groups[key].append(ret)
    #             else:
    #                 groups[key] = [ret]
    #
    #         for g, ret in groups.items():
    #
    #             # Esto no deberia pasar
    #             if not len(ret):
    #                 continue
    #
    #             if not ret[0].certificate_no:
    #                 __import__('ipdb').set_trace()
    #                 certificate_no = sequence_obj.get(
    #                     ret[0].retention_id.sequence_type_id.code)
    #                 for r in ret:
    #                     r.write({'certificate_no': certificate_no})
    #
    #     return move_lines

    # def write(self, cr, uid, ids, vals, context=None):
    #     if 'date_effective' in vals:
    #         date_applied = vals['date_effective']
    #
    #         # TODO: Mejorar este tema, podriamos escribir todas de golpe.
    #         # No mejora mucho tampoco.
    #         for v in self.browse(cr, uid, ids, context=context):
    #             for rl in v.retention_ids:
    #                 self.pool.get('retention.tax.line').write(
    #                     cr, uid, rl.id, {
    #                         'date_applied': date_applied,
    #                     }, context=context)
    #
    #     res = super(AccountPaymentOrder, self).write(cr, uid, ids,
    #                                                  vals, context=context)
    #     return res

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
            if po.disable_retentions or not (
                    po.income_line_ids + po.debt_line_ids):
                po.retention_ids = False
                continue

            prev_rets = []
            for ret in po.retention_ids:
                if ret.manual:
                    prev_rets.append(ret)

            vals = po.calculate_retentions()

            _logger.info("Retentions to create: %s" % pf(vals))
            po.retention_ids = [(0, 0, val) for val in vals]

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
                raise except_orm(
                    _("Error!"),
                    _("Voucher %s [id: %s] has Unlinkable Retentions:\n" +
                      "%s") % (
                          voucher.name, voucher.id,
                          ("\n").join(["%s [id: %s]" % (r.name, r.id) for r
                                       in u_rets])))
        return True
