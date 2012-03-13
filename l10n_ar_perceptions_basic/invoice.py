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
        #'factor_base': fields.function(_count_factor, method=True, string='Multipication factor for Base code', type='float', multi="all"),
        #'factor_tax': fields.function(_count_factor, method=True, string='Multipication factor Tax code', type='float', multi="all")
        'certificate_no': fields.char('Certificate No.', required=True, size=32),
        'ait_id': fields.many2one('account.invoice.tax', 'Invoice Tax', ondelete='cascade'),
    }

    def onchange_perception(self, cr, uid, ids, perception_id, context):
        perception_obj = self.pool.get('perception.perception')
        perception = perception_obj.browse(cr, uid, perception_id)
        vals = {}
        vals['name'] = perception.name
        vals['account_id'] = perception.tax_id.account_collected_id.id
        vals['base_code_id'] = perception.tax_id.base_code_id.id
        vals['tax_code_id'] = perception.tax_id.tax_code_id.id
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

    def write(self, cr, uid, ids, vals, context={}):
        ait_obj = self.pool.get('account.invoice.tax')
        res = self.browse(cr, uid, ids, context)[0]
        invoice_id = res.invoice_id.id

        # Posible valores que pueden cambiar
        possible_keys = ['name', 'account_id', 'base', 'amount', 'sequence', 'base_code_id', 'tax_code_id']

        ait_vals = {}
        for plt in self.browse(cr, uid, ids):
            if plt.ait_id and plt.ait_id.id:
                for k in possible_keys:
                    if k in vals:
                        ait_vals[k] = vals[k]

                # Computamos tax_amount y base_amount
                tax_amount, base_amount = self._compute(cr, uid, vals['perception_id'], invoice_id, vals['base'], vals['amount'], context)
                ait_vals['tax_amount'] = tax_amount
                ait_vals['base_amount'] = base_amount
                ait_obj.write(cr, uid, plt.ait_id.id, ait_vals)

        return super(perception_tax_line, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context={}):
        ait_obj = self.pool.get('account.invoice.tax')

        # Computamos tax_amount y base_amount
        tax_amount, base_amount = self._compute(cr, uid, vals['perception_id'], vals['invoice_id'], vals['base'], vals['amount'], context)

        # Creamos la account_invoice_tax
        ait_vals = {
                'invoice_id': vals['invoice_id'],
                'name': vals['name'],
                'account_id': vals['account_id'],
                'base': vals['base'],
                'amount': vals['amount'],
                'sequence': 10,
                'base_code_id': vals['base_code_id'],
                'tax_code_id': vals['tax_code_id'],
                'base_amount': base_amount,
                'tax_amount': tax_amount,
                }

        # Creamos el account.invoice.tax y dejamos una referencia en
        # el objeto perception.line.tax
        id = ait_obj.create(cr, uid, ait_vals)
        vals['ait_id'] = id
        return super(perception_tax_line, self).create(cr, uid, vals, context=context)

    def unlink(self, cr, uid, ids, context={}):
        ait_obj = self.pool.get('account.invoice.tax')

        for plt in self.browse(cr, uid, ids):
            if plt.ait_id and plt.ait_id.id:
                ait_obj.unlink(cr, uid, plt.ait_id.id, context)

        return super(perception_tax_line, self).unlink(cr, uid, ids, context=context)

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
        import pdb
        pdb.set_trace()
        plt_obj = self.pool.get('perception.tax.line')
        company_currency = invoice_browse.company_id.currency_id.id
        current_currency = invoice_browse.currency_id.id

        for p in invoice_browse.perception_ids:
            print 'Perception: ', p.name
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

            move_lines.insert(len(move_lines)-1, (0, 0, move_line))
        return move_lines

account_invoice()
