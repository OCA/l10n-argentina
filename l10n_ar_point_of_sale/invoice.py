# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012-2014 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#    All Rights Reserved. See AUTHORS for details.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import ValidationError
import re


class invoice(models.Model):
    _name = "account.invoice"
    _inherit = "account.invoice"
    _order = "date_invoice desc, internal_number desc"

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
            result = super(invoice, self).name_get()
        else:

            #reads = self.read(cr, uid, ids, ['pos_ar_id', 'type', 'is_debit_note', 'internal_number', 'denomination_id'], context=context)

            for inv in self:
                type = inv.type
                rtype = type
                number = inv.internal_number or ''
                denom = inv.denomination_id and inv.denomination_id.name or ''
                debit_note = inv.is_debit_note

                # Chequeo de Nota de Debito
                if  type == 'out_invoice':
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

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()

        if not self._context.get('use_internal_number', True):
            return super(invoice, self).name_search(name, args, operator, limit=limit)
        else:
            if name:
                recs = self.search([('internal_number','=',name)] + args, limit=limit)
            if not recs:
                recs = self.search([('internal_number',operator,name)] + args, limit=limit)
            if not recs:
                try:
                   recs = self.search([('pos_ar_id.name',operator,name)] + args, limit=limit)
                except TypeError:
                   recs = []

        return recs.name_get()

    @api.one
    @api.depends('invoice_line.price_subtotal', 'tax_line.amount')
    def _amount_all_ar(self):
        account_invoice_tax = self.env['account.invoice.tax']
        account_tax = self.env['account.tax']
        ctx = dict(self._context)
        amount_tax = 0.0
        amount_base = 0.0
        amount_exempt = 0.0
        for taxe in account_invoice_tax.compute(self.with_context(ctx)).values():
            amount_tax += taxe['amount']
            tax = account_tax.browse(taxe['tax_id'])
            tax_group = tax.tax_group
            amount_exempt += tax_group == 'vat' and taxe['is_exempt'] and taxe['base'] or 0.0
            amount_base +=  tax_group == 'vat' and not taxe['is_exempt'] and taxe['base'] or 0.0

        self.amount_tax = amount_tax
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line)
        self.amount_total = self.amount_untaxed + self.amount_tax


        self.amount_no_taxed = self.amount_untaxed - amount_base - amount_exempt
        self.amount_taxed = amount_base
        self.amount_exempt = amount_exempt

#    def _get_invoice_line(self, cr, uid, ids, context=None):
#        result = {}
#        for line in self.pool.get('account.invoice.line').browse(cr, uid, ids, context=context):
#            result[line.invoice_id.id] = True
#        return result.keys()
#
#    def _get_invoice_tax(self, cr, uid, ids, context=None):
#        result = {}
#        for tax in self.pool.get('account.invoice.tax').browse(cr, uid, ids, context=context):
#            result[tax.invoice_id.id] = True
#        return result.keys()

    pos_ar_id = fields.Many2one('pos.ar',string='Point of Sale', readonly=True, states={'draft':[('readonly',False)]})
    is_debit_note = fields.Boolean('Debit Note', default=False)
    denomination_id = fields.Many2one('invoice.denomination', readonly=True, states={'draft':[('readonly',False)]})
    internal_number = fields.Char(string='Invoice Number', size=32, readonly=True, states={'draft':[('readonly',False)]}, help="Unique number of the invoice, computed automatically when the invoice is created.")
    amount_untaxed = fields.Float(string='Subtotal', digits=dp.get_precision('Account'), store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_exempt = fields.Float(string='Amount Exempt', digits=dp.get_precision('Account'), store=True, readonly=True, compute='_amount_all_ar')
    amount_no_taxed = fields.Float(string='No Taxed', digits=dp.get_precision('Account'), store=True, readonly=True, compute='_amount_all_ar')
    amount_taxed = fields.Float(string='Taxed', digits=dp.get_precision('Account'), store=True, readonly=True, compute='_amount_all_ar')
    amount_untaxed = fields.Float(string='Subtotal', digits=dp.get_precision('Account'), store=True, readonly=True, compute='_amount_all_ar')
    amount_tax = fields.Float(string='Tax', digits=dp.get_precision('Account'), store=True, readonly=True, compute='_amount_all_ar')
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'), store=True, readonly=True, compute='_amount_all_ar')
    local = fields.Boolean(string='Local', default=True)

    #Validacion para que el total de una invoice no pueda ser negativo.
    @api.one
    @api.constrains('amount_total')
    def _check_amount_total(self):
        if self.amount_total < 0:
            raise ValidationError(_('Error! The total amount cannot be negative'))

#    @api.one
#    @api.constrains('denomination_id', 'pos_ar_id', 'type', 'is_debit_note', 'internal_number')
#    def _check_duplicate(self):
#
#        denomination_id = self.denomination_id
#        pos_ar_id = self.pos_ar_id
#        partner_id = self.partner_id or False
#        company_id = self.company_id or False
#
#        partner_country = partner_id.country_id
#        company_country = company_id.country_id
#
#        if self.type in ('in_invoice', 'in_refund'):
#            local = (partner_country  == company_country) or partner_country == False
#
#            # Si no es local, no hacemos chequeos
#            if not local:
#                return
#
#        # Si la factura no tiene seteado el numero de factura, devolvemos True, porque no sabemos si estara
#        # duplicada hasta que no le pongan el numero
#        if not invoice['internal_number']:
#            return
#
#        if self.type in ('out_invoice', 'out_refund'):
#            count = self.search_count([('denomination_id','=',denomination_id.id), ('pos_ar_id','=',pos_ar_id.id), ('is_debit_note','=',self.is_debit_note), ('internal_number','!=', False), ('internal_number','!=',''), ('internal_number','=',self.internal_number), ('type','=',self.type), ('state','!=','cancel')])
#
#            if count > 1:
#                raise ValidationError(_('Error! The Invoice is duplicated.'))
#        else:
#            count = self.search_count([('denomination_id','=',denomination_id.id), ('is_debit_note','=',self.is_debit_note), ('partner_id','=',partner_id.id), ('internal_number','!=', False), ('internal_number','!=',''), ('internal_number','=', self.internal_number), ('type','=',self.type), ('state','!=','cancel')])
#            if count > 1:
#                raise ValidationError(_('Error! The Invoice is duplicated.'))

    @api.one
    def _check_fiscal_values(self):
        # Si es factura de cliente
        denomination_id = self.denomination_id and self.denomination_id.id
        if self.type in ('out_invoice', 'out_refund', 'out_debit'):

            if not denomination_id:
                raise ValidationError(_('Denomination not set in invoice'))

            if not self.fiscal_position:
                raise ValidationError(_('Fiscal Position not set in invoice'))
#                if inv.pos_ar_id.denomination_id:
#                    self.write(cr, uid, inv.id, {'denomination_id' : inv.pos_ar_id.denomination_id.id})
#                    denomination_id = inv.pos_ar_id.denomination_id.id
#                else:
#                    raise osv.except_osv(_('Error!'), _('Denomination not set neither in invoice nor point of sale'))
#            else:
            if not self.pos_ar_id:
                raise ValidationError(_('You have to select a Point of Sale.'))

            if self.pos_ar_id.denomination_id.id != denomination_id:
                raise ValidationError(_('Point of sale has not the same denomination as the invoice.'))

            # Chequeamos que la posicion fiscal y la denomination_id coincidan
            if self.fiscal_position.denomination_id.id != denomination_id:
                raise ValidationError(_('The invoice denomination does not corresponds with this fiscal position.'))

        # Si es factura de proveedor
        else:
            if not denomination_id:
                raise ValidationError(_('Denomination not set in invoice'))

            # Chequeamos que la posicion fiscal y la denomination_id coincidan
            if self.fiscal_position.denom_supplier_id.id != self.denomination_id.id:
                raise ValidationError(_('The invoice denomination does not corresponds with this fiscal position.'))

        # Chequeamos que la posicion fiscal de la factura y del cliente tambien coincidan
        if self.fiscal_position.id != self.partner_id.property_account_position.id:
            raise ValidationError(_('The invoice fiscal position is not the same as the partner\'s fiscal position.'))


    @api.model
    def _update_reference(self, ref):
        self.ensure_one()
        move_id = self.move_id and self.move_id.id or False
        self.env.cr.execute('UPDATE account_move SET ref=%s ' \
                'WHERE id=%s', # AND (ref is null OR ref = \'\')',
                (ref, move_id))
        self.env.cr.execute('UPDATE account_move_line SET ref=%s ' \
                'WHERE move_id=%s', # AND (ref is null OR ref = \'\')',
                (ref, move_id))
        self.env.cr.execute('UPDATE account_analytic_line SET ref=%s ' \
                'FROM account_move_line ' \
                'WHERE account_move_line.move_id = %s ' \
                    'AND account_analytic_line.move_id = account_move_line.id',
                    (ref, move_id))
        return True

    @api.one
    def get_next_invoice_number(self):
        """Funcion para obtener el siguiente numero de comprobante correspondiente en el sistema"""

        # Obtenemos el ultimo numero de comprobante para ese pos y ese tipo de comprobante
        self.env.cr.execute("select max(to_number(substring(internal_number from '[0-9]{8}$'), '99999999')) from account_invoice where internal_number ~ '^[0-9]{4}-[0-9]{8}$' and pos_ar_id=%s and state in %s and type=%s and is_debit_note=%s", (self.pos_ar_id.id, ('open', 'paid', 'cancel',), self.type, self.is_debit_note))
        last_number = self.env.cr.fetchone()

        # Si no devuelve resultados, es porque es el primero
        if not last_number or not last_number[0]:
            next_number = 1
        else:
            next_number = last_number[0] + 1

        return next_number

    @api.multi
    def action_number(self):
        next_number = None
        invoice_vals = {}

        #TODO: not correct fix but required a fresh values before reading it
        # Esto se usa para forzar a que recalcule los campos funcion
        self.write({})

        for inv in self:

            local = True
            if self.type in ('in_invoice', 'in_refund'):
                local = self.fiscal_position.local

            #move_id = obj_inv.move_id and obj_inv.move_id.id or False
            reference = inv.reference or ''

            if local:
                inv._check_fiscal_values()

            # si el usuario no ingreso un numero, busco el ultimo y lo incremento , si no hay ultimo va 1.
            # si el usuario hizo un ingreso dejo ese numero
            internal_number = False
            next_number = False

            # Si son de Cliente
            if inv.type in ('out_invoice', 'out_refund'):

                pos_ar = inv.pos_ar_id
                next_number = self.get_next_invoice_number()[0]

                # Nos fijamos si el usuario dejo en blanco el campo de numero de factura
                if inv.internal_number:
                    internal_number = inv.internal_number

                # Lo ponemos como en Proveedores, o sea, A0001-00000001
                if not internal_number:
                    internal_number = '%s-%08d' % (pos_ar.name, next_number)

                m = re.match('^[0-9]{4}-[0-9]{8}$', internal_number)
                if not m:
                    raise ValidationError(_('The Invoice Number should be the format XXXX-XXXXXXXX'))

                # Escribimos el internal number
                invoice_vals['internal_number'] = internal_number

            # Si son de Proveedor
            else:
                if not inv.internal_number:
                    raise ValidationError(_('The Invoice Number should be filled'))

                if local:
                    m = re.match('^[0-9]{4}-[0-9]{8}$', inv.internal_number)
                    if not m:
                        raise ValidationError(_('The Invoice Number should be the format XXXX-XXXXXXXX'))

            # Escribimos los campos necesarios de la factura
            inv.write(invoice_vals)

            invoice_name = inv.name_get()[0][1]
            if not reference:
                ref = invoice_name
            else:
                ref = '%s [%s]' % (invoice_name, reference)

            # Actulizamos el campo reference del move_id correspondiente a la creacion de la factura
            inv._update_reference(ref)
        return True

    def refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None, context=None):

        #devuelve los ids de las invoice modificadas
        inv_ids = super(invoice , self).refund(cr, uid, ids, date, period_id, description, journal_id, context=context)

        #busco los puntos de venta de las invoices anteriores
        inv_obj = self.browse(cr, uid , ids , context=None)
        for obj in inv_obj:
            self.write(cr, uid , inv_ids , {'pos_ar_id': obj.pos_ar_id.id, 'denomination_id': obj.denomination_id.id} , context=None)

        return inv_ids

    @api.multi
    def onchange_partner_id(self, type, partner_id, date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False):
        res = super(invoice, self).onchange_partner_id(type, partner_id, date_invoice, payment_term, partner_bank_id, company_id)

        if partner_id:
            company_id = self.env['res.partner'].browse(partner_id).company_id.id
            fiscal_position_id = res['value']['fiscal_position']

            # HACK: Si no encontramos una fiscal position, buscamos una property que nos de el default
            # En realidad, si tenemos esa property creada desde el principio, todos los partners tendrian
            # su posicion fiscal. Pero si ya tenemos varios partners creados sin posicion fiscal, leemos
            # la property que creamos de la posicion fiscal para que quede como default y asi no tenemos
            # que hacerle muchas modificaciones al sistema. Igualmente, al setear una property que sea Global
            # ya no hace falta buscarla por codigo porque se la asigna solito a todos los que no tenian.
            if not fiscal_position_id:
                property_obj = self.env['ir.property']
                fpos_pro = property_obj.search([('name', '=', 'property_account_position'), ('company_id', '=', company_id)], limit=1)
                if not fpos_pro:
                    return res
                fpos_line_data = fpos_pro.read(['name', 'value_reference', 'res_id'])
                fiscal_position_id = fpos_line_data and fpos_line_data[0].get('value_reference', False) and int(fpos_line_data[0]['value_reference'].split(',')[1]) or False
            fiscal_pool = self.env['account.fiscal.position']
            pos_pool = self.env['pos.ar']
            if fiscal_position_id:
                fiscal_position = fiscal_pool.browse(fiscal_position_id)
                res['value'].update({'fiscal_position': fiscal_position_id})
                denomination_id = fiscal_position.denomination_id.id
                res.update({'domain': {'pos_ar_id': [('denomination_id', '=', denomination_id)]}})

                if type in ['in_invoice', 'in_refund', 'in_debit']:  # Supplier invoice
                    denom_sup_id = fiscal_position.denom_supplier_id.id
                    res['value'].update({'denomination_id': denom_sup_id})
                else:  # Customer invoice
                    pos = pos_pool.search([('denomination_id', '=', denomination_id)], order='priority asc', limit=1)
                    if len(pos):
                        res['value'].update({'local': fiscal_position.local,
                                             'denomination_id': denomination_id,
                                             'pos_ar_id': pos[0].id})

        else:
            res['value']['local'] = True
        return res

    def invoice_pay_customer(self, cr, uid, ids, context=None):
        if not ids: return []
        inv = self.browse(cr, uid, ids[0], context=context)
        res = super(invoice, self).invoice_pay_customer(cr, uid, ids, context=context)
        res['context']['type'] = inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'

        return res

invoice()


class account_invoice_tax(models.Model):
    _name = "account.invoice.tax"
    _inherit = "account.invoice.tax"

    tax_id = fields.Many2one('account.tax', string='Account Tax', required=True)
    is_exempt = fields.Boolean(string='Is Exempt', readonly=True)

    @api.onchange('tax_id')
    def tax_id_change(self):
        self.name = self.tax_id.description
        if self.invoice_id.type in ('out_invoice', 'in_invoice'):
            self.base_code_id = self.tax_id.base_code_id.id
            self.tax_code_id = self.tax_id.tax_code_id.id
            self.account_id = self.tax_id.account_collected_id.id
        else:
            self.base_code_id = self.tax_id.ref_base_code_id.id
            self.tax_code_id = self.tax_id.ref_tax_code_id.id
            self.account_id = self.tax_id.account_paid_id.id

    @api.v8
    def hook_compute_invoice_taxes(self, invoice, tax_grouped):
        return tax_grouped

    @api.v8
    def compute(self, invoice):
        tax_grouped = {}

        currency = invoice.currency_id.with_context(date=invoice.date_invoice or fields.Date.context_today(invoice))
        company_currency = invoice.company_id.currency_id

        for line in invoice.invoice_line:
            taxes = line.invoice_line_tax_id.compute_all(
                    (line.price_unit * (1-(line.discount or 0.0)/100.0)),
                    line.quantity, line.product_id, invoice.partner_id)['taxes']
            for tax in taxes:
                # TODO: Tal vez se pueda cambiar el boolean is_exempt por un type (selection)
                # para despues incluir impuestos internos, retenciones, percepciones, o sea,
                # distintos tipos de impuestos
                tax_browse = self.env['account.tax'].browse(tax['id'])
                val = {
                    'invoice_id': invoice.id,
                    'name': tax['name'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'is_exempt': tax_browse.is_exempt,
                    'base': currency.round(tax['price_unit'] * line['quantity']),
                    'tax_id': tax['id'],
                }

                if invoice.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['ref_base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['ref_tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_paid_id']

                # If the taxes generate moves on the same financial account as the invoice line
                # and no default analytic account is defined at the tax level, propagate the
                # analytic account from the invoice line to the tax line. This is necessary
                # in situations were (part of) the taxes cannot be reclaimed,
                # to ensure the tax move is allocated to the proper analytic account.
                if not val.get('account_analytic_id') and line.account_analytic_id and val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = line.account_analytic_id.id

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = currency.round(t['base'])
            t['amount'] = currency.round(t['amount'])
            t['base_amount'] = currency.round(t['base_amount'])
            t['tax_amount'] = currency.round(t['tax_amount'])

        # Agregamos un hook por si otros modulos quieren agregar sus taxes
        tax_grouped = self.hook_compute_invoice_taxes(invoice, tax_grouped)

        return tax_grouped
