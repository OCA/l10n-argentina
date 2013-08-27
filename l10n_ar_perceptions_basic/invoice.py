# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2011
#
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from osv import osv, fields
import decimal_precision as dp
import time

class perception_tax_line(osv.osv):
    _name = "perception.tax.line"
    _description = "Perception Tax Line"

    #TODO: Tal vaz haya que ponerle estados a este objeto para manejar tambien propiedades segun estados
    _columns = {
        'name': fields.char('Perception', required=True, size=64),
        'date': fields.date('Date', select=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice', ondelete='cascade'),
        'account_id': fields.many2one('account.account', 'Tax Account', required=True,
                                      domain=[('type','<>','view'),('type','<>','income'), ('type', '<>', 'closed')]),
        'base': fields.float('Base', digits_compute=dp.get_precision('Account')),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account')),
        'perception_id': fields.many2one('perception.perception', 'Perception Configuration', required=True, help="Perception configuration used '\
                                       'for this perception tax, where all the configuration resides. Accounts, Tax Codes, etc."),
        'base_code_id': fields.many2one('account.tax.code', 'Base Code', help="The account basis of the tax declaration."),
        'base_amount': fields.float('Base Code Amount', digits_compute=dp.get_precision('Account')),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Code', help="The tax basis of the tax declaration."),
        'tax_amount': fields.float('Tax Code Amount', digits_compute=dp.get_precision('Account')),
        'company_id': fields.related('account_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'partner_id': fields.related('invoice_id', 'partner_id', type='many2one', relation='res.partner', string='Partner', readonly=True),
        'vat': fields.related('invoice_id', 'partner_id', 'vat', type='char', string='CIF/NIF', readonly=True),
        'state_id': fields.many2one('res.country.state', string="State/Province"),
        'ait_id': fields.many2one('account.invoice.tax', 'Invoice Tax', ondelete='cascade'),
    }

    def onchange_perception(self, cr, uid, ids, perception_id, context):
        if not perception_id:
            return {}
        perception_obj = self.pool.get('perception.perception')
        perception = perception_obj.browse(cr, uid, perception_id)
        vals = {}
        vals['name'] = perception.name
        vals['account_id'] = perception.tax_id.account_collected_id.id
        vals['base_code_id'] = perception.tax_id.base_code_id.id
        vals['tax_code_id'] = perception.tax_id.tax_code_id.id
        vals['state_id'] = perception.state_id.id
        return {'value': vals}

    def _compute(self, cr, uid, perception_id, invoice_id, base, amount, context={}):
        # Buscamos la account_tax referida a esta perception_id
        cur_obj = self.pool.get('res.currency')
        inv_obj = self.pool.get('account.invoice')
        perception_obj = self.pool.get('perception.perception')

        perception = perception_obj.browse(cr, uid, perception_id, context)
        tax = perception.tax_id

        # Nos fijamos la currency de la invoice
        inv = inv_obj.browse(cr, uid, invoice_id)
        company_currency = inv.company_id.currency_id.id

        base_amount = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, base * tax.base_sign, context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
        tax_amount = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, amount * tax.tax_sign, context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
        return (tax_amount, base_amount)

perception_tax_line()


class account_invoice(osv.osv):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    _columns = {
            'perception_ids': fields.one2many('perception.tax.line', 'invoice_id', 'Perception', readonly=True, states={'draft':[('readonly', False)]}),
            }

    def finalize_invoice_move_lines(self, cr, uid, invoice_browse, move_lines):
        """finalize_invoice_move_lines(cr, uid, invoice, move_lines) -> move_lines
        Hook method to be overridden in additional modules to verify and possibly alter the
        move lines to be created by an invoice, for special cases.
        :param invoice_browse: browsable record of the invoice that is generating the move lines
        :param move_lines: list of dictionaries with the account.move.lines (as for create())
        :return: the (possibly updated) final move_lines to create for this invoice
        """
        # Como nos faltan los account.move.line de las bases imponibles de las percepciones
        # utilizamos este hook para agregarlos
        plt_obj = self.pool.get('perception.tax.line')
        company_currency = invoice_browse.company_id.currency_id.id
        current_currency = invoice_browse.currency_id.id

        for p in invoice_browse.perception_ids:
            sign = p.perception_id.tax_id.base_sign
            tax_amount, base_amount = plt_obj._compute(cr, uid, p.perception_id.id, invoice_browse.id, p.base, p.amount)

            # ...y ahora creamos la linea contable perteneciente a la base imponible de la perception
            # Notar que credit & debit son 0.0 ambas. Lo que cuenta es el tax_code_id y el tax_amount
            move_line = {
                'name': p.name + '(Base Imp)',
                'ref': invoice_browse.internal_number or False,
                'debit': 0.0,
                'credit': 0.0,
                'account_id': p.account_id.id,
                'tax_code_id': p.base_code_id.id,
                'tax_amount': base_amount,
                'journal_id': invoice_browse.journal_id.id,
                'period_id': invoice_browse.period_id.id,
                'partner_id': invoice_browse.partner_id.id,
                'currency_id': company_currency <> current_currency and  current_currency or False,
                'amount_currency': company_currency <> current_currency and sign * p.amount or 0.0,
                'date': invoice_browse.date_invoice or time.strftime('%Y-%m-%d'),
                'date_maturity': invoice_browse.date_due or False,
            }

            # Si no tenemos seteada la fecha, escribimos la misma que la de la factura
            if not p.date:
                plt_obj.write(cr, uid, p.id, {'date': move_line['date']})

            move_lines.insert(len(move_lines)-1, (0, 0, move_line))
        return move_lines

account_invoice()


class account_invoice_tax(osv.osv):
    _name = "account.invoice.tax"
    _inherit = "account.invoice.tax"

    # Aca le agregamos las account_invoice_taxes pertenecientes a las Percepciones
    def hook_compute_invoice_taxes(self, cr, uid, invoice_id, tax_grouped, context=None):

        percep_tax_line_obj = self.pool.get('perception.tax.line')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        cur = inv.currency_id

        # Recorremos las percepciones y las computamos como account.invoice.tax
        for line in inv.perception_ids:
            val={}
            tax = line.perception_id.tax_id
            val['invoice_id'] = inv.id
            val['name'] = line.name
            val['amount'] = line.amount
            val['manual'] = False
            val['sequence'] = 10
            val['is_exempt'] = False
            val['base'] = line.base
            val['tax_id'] = tax.id

            # Computamos tax_amount y base_amount
            tax_amount, base_amount = percep_tax_line_obj._compute(cr, uid, line.perception_id.id, invoice_id,
                                                                   val['base'], val['amount'], context)

            if inv.type in ('out_invoice','in_invoice'):
                val['base_code_id'] = line.base_code_id.id
                val['tax_code_id'] = line.tax_code_id.id
                val['base_amount'] = base_amount
                val['tax_amount'] = tax_amount
                val['account_id'] = tax.account_collected_id.id
            else:
                val['base_code_id'] = tax.ref_base_code_id.id
                val['tax_code_id'] = tax.ref_tax_code_id.id
                val['base_amount'] = base_amount
                val['tax_amount'] = tax_amount
                val['account_id'] = tax.account_paid_id.id

            key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
            if not key in tax_grouped:
                tax_grouped[key] = val
            else:
                tax_grouped[key]['amount'] += val['amount']
                tax_grouped[key]['base'] += val['base']
                tax_grouped[key]['base_amount'] += val['base_amount']
                tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = cur_obj.round(cr, uid, cur, t['base'])
            t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
            t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
            t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])

        return super(account_invoice_tax, self).hook_compute_invoice_taxes(cr, uid, invoice_id, tax_grouped, context)

account_invoice_tax()
