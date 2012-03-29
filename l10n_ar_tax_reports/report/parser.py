# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2012 E-MIPS Electronica e Informatica
#                       info@e-mips.com.ar
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

from report import report_sxw
import random

class Parser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'hello_world':self.hello_world,
            'set_period':self._set_period,
            'get_lines':self.get_lines,
            'get_columns':self.get_columns,
        })
        self.period_id = None
        self.columns = None

    def _set_period(self, period_id):
        self.period_id = period_id

    def get_columns(self, config_id):

        # Obtenemos los tax_code que tuvieron movimientos en el periodo pedido
        q = "SELECT DISTINCT at.id, at.name, at.code " \
        "FROM account_tax_code at, account_period p, account_move_line l, account_invoice i " \
        "WHERE p.id=l.period_id AND at.id=l.tax_code_id AND p.id=%s " \
        "AND i.type IN ('out_invoice', 'out_debit', 'out_refund') AND i.move_id=l.move_id " \
        "AND at.id IN (SELECT tax_code_id FROM subjournal_report_taxcode_column " \
        "WHERE report_config_id=%s) ORDER BY at.code"

        self.cr.execute(q, (self.period_id, config_id))
        res = self.cr.fetchall()
        self.columns = res
        return res

    def get_lines(self):
        tax_code_ids = [col[0] for col in self.columns]

        self.cr.execute("SELECT l.id FROM account_move_line l, account_invoice i, " \
        "account_tax_code tc, account_period ap " \
        "WHERE i.move_id=l.move_id AND tc.id=l.tax_code_id  " \
        "AND i.type IN ('out_invoice', 'out_debit', 'out_refund') " \
        "AND ap.id=l.period_id AND ap.id=%s " \
        "AND tc.id IN %s", (self.period_id, tuple(tax_code_ids)))

        # Obtenemos el resultado de la consulta
        res = self.cr.fetchall()

        # Lineas
        line_ids = map(lambda x: x[0], res)

        account_obj = self.pool.get('account.move.line')
        #ids = account_obj.search(self.cr, self.uid, [('invoice','!=',False), ('tax_code_id','!=',False)])
        lines = {}
        total_invoiced = 0.0
        for l in account_obj.browse(self.cr, self.uid, line_ids):
            line = {}

            # Calculamos el signo
            sign = 1
            if l.invoice.type in ('out_refund', 'in_refund'):
                sign = -1

            if not l.move_id.id in lines:
                line['date'] = l.date
                line['partner'] = l.partner_id.name
                line['vat'] = l.partner_id.vat
                line['fiscal_position'] = l.partner_id.property_account_position.name
                line['invoice_type'] = self.get_invoice_type(l.invoice)
                line['invoice_number'] = l.invoice.internal_number
                line['taxes'] = []
                line['taxes'] += ['']*len(tax_code_ids)
                line['total'] = l.invoice.amount_total*sign
                total_invoiced += line['total']
                lines[l.move_id.id] = line

            for i, t_id in enumerate(tax_code_ids):
                if l.tax_code_id.id == t_id:
                    lines[l.move_id.id]['taxes'][i] =l.tax_amount*sign

        res = [v for k,v in lines.iteritems()]

        line['date'] = ""
        line['partner'] = ""
        line['vat'] = ""
        line['fiscal_position'] = ""
        line['invoice_type'] = ""
        line['invoice_number'] = ""
        line['taxes'] = []
        line['total'] = total_invoiced

        # Obtenemos los totales
        tax_sums = self.get_sum()

        for t_id, sum in tax_sums:
            line['taxes'].append(sum)
        res.append(line)

        return res#account_obj.browse(self.cr, self.uid, line_ids)


    def get_sum(self):
        tax_code_ids = [col[0] for col in self.columns]

        self.cr.execute("SELECT l.tax_code_id, sum(l.tax_amount) as sum_amount " \
        "FROM account_move_line l, account_invoice i,  " \
        "account_tax_code tc, account_period ap " \
        "WHERE i.move_id=l.move_id AND tc.id=l.tax_code_id  " \
        "AND i.type IN ('out_invoice', 'out_debit', 'out_refund') " \
        "AND ap.id=l.period_id AND ap.id=%s AND tc.id IN %s " \
        "GROUP BY l.tax_code_id ORDER BY l.tax_code_id", (self.period_id, tuple(tax_code_ids)))

        res = self.cr.fetchall()
        print 'Sumas: ', res
        return res

    def get_invoice_type(self, inv):
        type = ""
        denomination = ""

        if inv == False:
            return ""

        if inv.type in ('out_invoice', 'in_invoice'):
            type = "F"
        elif inv.type in ('out_debit', 'in_debit'):
            type = "ND"
        else:
            type = "NC"

        if inv.pos_ar_id and inv.pos_ar_id.denomination_id:
            denomination = inv.pos_ar_id.denomination_id.name
        elif inv.denomination_id:
            denomination = inv.denomination_id.name

        return '%s %s' % (type, denomination)

    def hello_world(self, name):
        return "Hello, %s!" % name

