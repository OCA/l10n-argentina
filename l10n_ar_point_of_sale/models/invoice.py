###############################################################################
#   Copyright (c) 2017-2018 Eynes/E-MIPS (http://www.e-mips.com.ar)
#   Copyright (c) 2014-2018 Aconcagua Team
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################


import re
import logging
from odoo.addons import decimal_precision as dp
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _name = "account.invoice"
    _inherit = "account.invoice"
    _order = "date_invoice desc, internal_number desc"

    pos_ar_id = fields.Many2one(comodel_name='pos.ar',
                                string='Point of Sale',
                                readonly=True,
                                states={'draft': [('readonly', False)]})
    is_debit_note = fields.Boolean(string='Debit Note', default=False)
    denomination_id = fields.Many2one(comodel_name='invoice.denomination',
                                      readonly=True,
                                      states={'draft': [('readonly', False)]})
    internal_number = fields.Char(string='Invoice Number', size=32,
                                  readonly=True,
                                  states={'draft': [('readonly', False)]},
                                  help="Unique number of the invoice, computed \
                                  automatically when the invoice is created.")
    amount_exempt = fields.Monetary(string='Amount Exempt',
                                    digits=dp.get_precision('Account'),
                                    store=True,
                                    readonly=True, compute='_compute_amount')
    amount_no_taxed = fields.Monetary(string='No Taxed',
                                      digits=dp.get_precision('Account'),
                                      store=True, readonly=True,
                                      compute='_compute_amount')
    amount_taxed = fields.Monetary(string='VAT Base',
                                   digits=dp.get_precision('Account'),
                                   store=True, readonly=True,
                                   compute='_compute_amount')
    amount_other_taxed = fields.Monetary(string='Other Tax Base',
                                         digits=dp.get_precision('Account'),
                                         store=True, readonly=True,
                                         compute='_compute_amount')
    local = fields.Boolean(string='Local', default=True)
    internal_number = fields.Char(string="Internal Number", default=False,
                                  copy=False, readonly=True,
                                  help="Unique number of the invoice, " +
                                  "computed automatically when the " +
                                  "invoice is created.")

    # DONE
    @api.multi
    def name_get(self):

        TYPES = {
            'out_invoice': _('CI '),
            'in_invoice': _('SI '),
            'out_refund': _('CR '),
            'in_refund': _('SR '),
            'out_debit': _('CD '),
            'in_debit': _('SD '),
        }
        result = []

        if not self._context.get('use_internal_number', True):
            result = super(AccountInvoice, self).name_get()
        else:

            # reads = self.read(cr, uid, ids, [
            #     'pos_ar_id', 'type',
            #     'is_debit_note',
            #     'internal_number',
            #     'denomination_id'], context=context)

            for inv in self:
                type = inv.type
                rtype = type
                number = inv.internal_number or ''
                denom = inv.denomination_id and inv.denomination_id.name or ''
                debit_note = inv.is_debit_note

                # Chequeo de Nota de Debito
                if type == 'out_invoice':
                    if debit_note:
                        rtype = 'out_debit'
                    else:
                        rtype = 'out_invoice'
                elif type == 'in_invoice':
                    if debit_note:
                        rtype = 'in_debit'
                    else:
                        rtype = 'in_invoice'

                name = TYPES[rtype] + denom + number
                result.append((inv.id, name))

        return result

    # DONE
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if not self._context.get('use_internal_number', True):
            return super(AccountInvoice, self).name_search(
                name, args, operator, limit=limit)
        else:
            if name:
                recs = self.search([('internal_number', '=', name)] +
                                   args, limit=limit)
            if not recs:
                recs = self.search([('internal_number', operator, name)] +
                                   args, limit=limit)
            # if not recs:
            #     try:
            #         recs = self.search([('pos_ar_id.name', operator, name)] +
            #                            args, limit=limit)
            #     except TypeError:
            #         recs = []

        return recs.name_get()

    @api.model
    def _update_reference(self, ref):
        # Ensure only one
        move_id = self.move_id.id
        self.env.cr.execute(
            'UPDATE account_move SET ref=%s '
            'WHERE id=%s',  # AND (ref is null OR ref = \'\')',
            (ref, move_id))
        self.env.cr.execute(
            'UPDATE account_move_line SET ref=%s '
            'WHERE move_id=%s',  # AND (ref is null OR ref = \'\')',
            (ref, move_id))
        self.env.cr.execute(
            'UPDATE account_analytic_line SET ref=%s '
            'FROM account_move_line '
            'WHERE account_move_line.move_id = %s '
            'AND account_analytic_line.move_id = account_move_line.id',
            (ref, move_id))
        return True

    # DONE
    # Se calculan los campos del pie de pagina de la factura
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount',
                 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type')
    def _compute_amount(self):
        super()._compute_amount()
        for invoice in self:
            invoice.amount_exempt = sum(
                line.price_subtotal for line in invoice.invoice_line_ids if
                any(map(lambda x: x.is_exempt, line.invoice_line_tax_ids)))
            invoice.amount_no_taxed = sum(
                line.price_subtotal for line in invoice.invoice_line_ids if
                not line.invoice_line_tax_ids)
            invoice.amount_taxed = sum(
                line.price_subtotal for line in invoice.invoice_line_ids if
                any(map(lambda x: (x.tax_group == 'vat' and not x.is_exempt),
                        line.invoice_line_tax_ids)))
            invoice.amount_other_taxed = sum(
                line.price_subtotal for line in invoice.invoice_line_ids if
                any(map(lambda x: (x.tax_group != 'vat' and not x.is_exempt),
                        line.invoice_line_tax_ids)))

    # TODO --Averiguar como cancelar una nota de credito pagada
    @api.multi
    def action_cancel(self):
        states = (
            'draft',
            'proforma2',
            'proforma',
            'open'
        )
        allowed_states = self.env.context.\
            get("cancel_states", states)
        for inv in self:
            if inv.type == "out_refund" and inv.state not in allowed_states:
                state_tags = [_(tag) for state, tag in
                              self._columns["state"].selection
                              if state in allowed_states]
                err = _("Credit Note can only be \
                    cancelled in these states: %s!")
                raise ValidationError(err % ', '.join(state_tags))

        return super(AccountInvoice, self).action_cancel()

    # def _get_invoice_line_ids(self, cr, uid, ids, context=None):
    #     result = {}bb
    #     for line in self.pool.get('account.invoice.line').\
    #             browse(cr, uid, ids, context=context):
    #         pass
    #         result[line.invoice_id.id] = True
    #     return result.keys()
    #
    # def _get_invoice_tax(self, cr, uid, ids, context=None):
    #     result = {}
    #     for tax in self.pool.get('account.invoice.tax').\
    #             browse(cr, uid, ids, context=context):
    #         result[tax.invoice_id.id] = True
    #     return result.keys()

    # TODO --Verificar si sigue siendo util esta validación. si
    # Validacion para que el total de una invoice no pueda ser negativo.
    # @api.one
    # @api.constrains('amount_total')
    # def _check_amount_total(self):
    #     if self.amount_total < 0:
    #         raise ValidationError(
    #             _('Error! The total amount cannot be negative'))

    # DONE
    @api.constrains('denomination_id', 'pos_ar_id', 'type',
                    'is_debit_note', 'internal_number')
    def _check_duplicate(self):
        for invoice in self:
            denomination_id = invoice.denomination_id
            pos_ar_id = invoice.pos_ar_id
            partner_id = invoice.partner_id or False

            if invoice.type in ('in_invoice', 'in_refund'):
                local = invoice.fiscal_position_id.local

                # Si no es local, no hacemos chequeos
                if not local:
                    return

            # Si la factura no tiene seteado el numero de factura,
            # devolvemos True, porque no sabemos si estara
            # duplicada hasta que no le pongan el numero
            if not invoice.internal_number:
                return

            if invoice.type in ('out_invoice', 'out_refund'):
                count = invoice.search_count([
                    ('denomination_id', '=', denomination_id.id),
                    ('pos_ar_id', '=', pos_ar_id.id),
                    ('is_debit_note', '=', invoice.is_debit_note),
                    ('internal_number', '!=', False),
                    ('internal_number', '!=', ''),
                    ('internal_number', '=', invoice.internal_number),
                    ('type', '=', invoice.type), ('state', '!=', 'cancel')])

                if count > 1:
                    raise ValidationError(
                        _('Error! The Invoice is duplicated.'))
            else:
                count = invoice.search_count([
                    ('denomination_id', '=', denomination_id.id),
                    ('is_debit_note', '=', invoice.is_debit_note),
                    ('partner_id', '=', partner_id.id),
                    ('internal_number', '!=', False),
                    ('internal_number', '!=', ''),
                    ('internal_number', '=', invoice.internal_number),
                    ('type', '=', invoice.type),
                    ('state', '!=', 'cancel')])

                if count > 1:
                    raise ValidationError(
                        _('Error! The Invoice is duplicated.'))

    # DONE
    @api.multi
    def _check_fiscal_values(self):
        for invoice in self:
            # Si es factura de cliente
            denomination = invoice.denomination_id
            if invoice.type in ('out_invoice', 'out_refund', 'out_debit'):

                if not denomination:
                    raise ValidationError(_('Denomination not set in invoice'))

                if not invoice.pos_ar_id:
                    raise ValidationError(
                        _('You have to select a Point of Sale.'))
                if denomination not in invoice.pos_ar_id.denomination_ids:
                    raise ValidationError(
                        _('Point of sale has ' +
                          'not the same denomination as the invoice.'))

                # Chequeamos que la posicion fiscal
                # y la denomination coincidan
                if invoice.fiscal_position_id.denomination_id != denomination:
                    raise ValidationError(
                        _('The invoice denomination does not ' +
                          'corresponds with this fiscal position.'))

            # Si es factura de proveedor
            else:
                if not denomination:
                    raise ValidationError(_('Denomination not set in invoice'))

                # Chequeamos que la posicion fiscal
                # y la denomination coincidan
                if invoice.fiscal_position_id.denom_supplier_id != \
                        denomination:
                    raise ValidationError(
                        _('The invoice denomination does not ' +
                          'corresponds with this fiscal position.'))

            # Chequeamos que la posicion fiscal de la
            # factura y del cliente tambien coincidan
            if invoice.fiscal_position_id != \
                    invoice.partner_id.property_account_position_id:
                raise ValidationError(
                    _('The invoice fiscal position is not ' +
                      'the same as the partner\'s fiscal position.'))

    # DONE
    @api.multi
    def get_next_invoice_number(self):
        """
        Funcion para obtener el siguiente
        numero de comprobante correspondiente
        en el sistema
        """
        self.ensure_one()
        offset = self.env.context.get('invoice_number_offset', 0)
        # Obtenemos el ultimo numero de comprobante
        # para ese pos y ese tipo de comprobante
        q = """
        SELECT MAX(TO_NUMBER(
            SUBSTRING(internal_number FROM '[0-9]{8}$'), '99999999')
            )
        FROM account_invoice
        WHERE internal_number ~ '^[0-9]{4}-[0-9]{8}$'
            AND pos_ar_id = %(pos_id)s
            AND state in %(state)s
            AND type = %(type)s
            AND is_debit_note = %(is_debit_note)s
            AND denomination_id = %(denomination_id)s
        """
        q_vals = {
            'pos_id': self.pos_ar_id.id,
            'state': ('open', 'paid', 'cancel',),
            'type': self.type,
            'is_debit_note': self.is_debit_note,
            'denomination_id': self.denomination_id.id,
        }
        self.env.cr.execute(q, q_vals)
        last_number = self.env.cr.fetchone()

        # Si no devuelve resultados, es porque es el primero
        if not last_number or not last_number[0]:
            next_number = 1
        else:
            next_number = last_number[0] + 1

        return int(next_number + offset)

    # DONE
    @api.multi
    def action_move_create(self):
        if self.local:
            self._check_fiscal_values()
        self.action_number()
        res = super(AccountInvoice, self).action_move_create()
        return res

    # DONE
    @api.multi
    def action_number(self):
        for inv in self:
            invoice_vals = {}
            # si el usuario no ingreso un numero, busco
            # el ultimo y lo incremento , si no hay ultimo va 1.
            # si el usuario hizo un ingreso dejo ese numero
            internal_number = False

            # Si son de Cliente
            if inv.type in ('out_invoice', 'out_refund'):

                pos_ar = inv.pos_ar_id
                next_number = self.get_next_invoice_number()

                # Nos fijamos si el usuario dejo en
                # blanco el campo de numero de factura
                if inv.internal_number:
                    internal_number = inv.internal_number

                # Lo ponemos como en Proveedores, o sea, A0001-00000001
                if not internal_number:
                    internal_number = '%s-%08d' % (pos_ar.name, next_number)

                m = re.match('^[0-9]{4}-[0-9]{8}$', internal_number)
                if not m:
                    raise ValidationError(
                        _('The Invoice Number should \
                            be the format XXXX-XXXXXXXX'))

                # Escribimos el internal number
                invoice_vals['internal_number'] = internal_number

            # Si son de Proveedor
            else:
                if not inv.internal_number:
                    raise ValidationError(
                        _('The Invoice Number should be filled'))

                if self.local:
                    m = re.match('^[0-9]{4}-[0-9]{8}$', inv.internal_number)
                    if not m:
                        raise ValidationError(
                            _('The Invoice Number should \
                                be the format XXXX-XXXXXXXX'))

            # Escribimos los campos necesarios de la factura
            inv.write(invoice_vals)
        return True

    @api.multi
    @api.returns('self')
    def refund(self, date_invoice=None, date=None,
               description=None, journal_id=None):

        # Devuelve los ids de las invoice modificadas
        inv_ids = super(AccountInvoice, self).\
            refund(date_invoice, date, description, journal_id)

        # Busco los puntos de venta de las invoices anteriores
        for inv in inv_ids:
            vals = {
                'pos_ar_id': self.pos_ar_id.id,
                'denomination_id': self.denomination_id.id
            }
            inv.write(vals)

        return inv_ids

    # DONE
    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        # Se llenan
        res = super(AccountInvoice, self)._onchange_partner_id()
        domain = {}
        if 'domain' in res:
            domain = res['domain']
        # Verifico que halla partner y posicion fiscal
        if self.partner_id and self.fiscal_position_id:
            # Verifico que sea factura de vendedor
            # o nota de credito de proveedor.
            # NOTA:
            # 'out_invoice': Factura de cliente
            # 'in_invoice': Factura de proveedor
            # 'out_refund': Nota de creidot de cliente
            # 'in_refund': Nota de credito de proveedor
            if self.type in ['in_invoice', 'in_refund']:
                self.denomination_id = self.fiscal_position_id.\
                    denom_supplier_id
            else:
                domain['pos_ar_id'] = [('denomination_id', '=',
                                        self.denomination_id)]
                self.denomination_id = self.fiscal_position_id.denomination_id
                sorted_pos = self.denomination_id.pos_ar_ids.sorted(
                    key=lambda x: x.priority)
                if sorted_pos:
                    self.pos_ar_id = sorted_pos[0]
            self.local = self.fiscal_position_id.local
        else:
            self.local = True
            self.denomination_id = False
            self.pos_ar_id = False
        return res

    # def invoice_pay_customer(self, cr, uid, ids, context=None):
    #     if not ids:
    #         return []
    #     inv = self.browse(cr, uid, ids[0], context=context)
    #     res = super(AccountInvoice, self).invoice_pay_customer(
    #         cr, uid, ids, context=context)
    #     res['context']['type'] = inv.type in \
    #         ('out_invoice', 'out_refund') and 'receipt' or 'payment'
    #     return res

    def _prepare_tax_line_vals(self, line, tax):
        vals = super(AccountInvoice, self)._prepare_tax_line_vals(line, tax)
        tax_browse = self.env['account.tax'].browse(tax['id'])
        vals['is_exempt'] = tax_browse.is_exempt
        vals['tax_id'] = tax['id']
        return vals


class AccountInvoiceTax(models.Model):
    _name = "account.invoice.tax"
    _inherit = "account.invoice.tax"

    tax_id = fields.Many2one('account.tax',
                             string='Account Tax',
                             required=True)
    is_exempt = fields.Boolean(string='Is Exempt',
                               readonly=True)
