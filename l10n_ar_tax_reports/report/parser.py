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

from openerp.osv import osv
from openerp.report import report_sxw
import random
from openerp.tools.translate import _


class Parser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'hello_world': self.hello_world,
            'get_title': self.get_title,
            'set_period': self._set_period,
            'get_lines': self.get_lines,
            'get_columns': self.get_columns,
            'set_context': self._set_context,
        })
        self.period_id = None
        self.columns = None
        self.based_on = None

    def _set_period(self, period_id):
        self.period_id = period_id[0]

    def _set_context(self, data):
        self.based_on = data['based_on']

    def _get_types(self):
        # print 'Based_on: ', self.based_on
        if self.based_on == 'sale':
            return ['out_invoice', 'out_refund', 'out_debit']
        else:
            return ['in_invoice', 'in_refund', 'in_debit']

    def get_title(self, company_id):
        #company = self.pool.get('res.company').browse(self.cr, self.uid, company_id)
        period = self.pool.get('account.period').browse(self.cr, self.uid, self.period_id)
        if self.based_on == 'sale':
            sub_type = 'Ventas'
        else:
            sub_type = 'Compras'

        title = '%s - IVA %s Periodo %s' % (company_id.name, sub_type, period.name)
        return title

    def get_columns(self, config_id):
        # Obtenemos los tax_code que tuvieron movimientos en el periodo pedido
        types = self._get_types()

        # TODO: Implementar el reporte con este SELECT sobre account_invoice_tax. Sería mejor.
#        q = "SELECT id from (SELECT DISTINCT tc.id, tc.code FROM account_tax_code tc, account_invoice_tax it, account_invoice i " \
#        "WHERE i.id=it.invoice_id AND tc.id=it.tax_code_id AND i.period_id=%s AND i.type in %s UNION ALL " \
#        "SELECT DISTINCT tc.id, tc.code FROM account_tax_code tc, account_invoice_tax it, account_invoice i " \
#        "WHERE i.id=it.invoice_id AND tc.id=it.base_code_id AND i.period_id=%s AND i.type in %s) as t_ids " \
#        "WHERE id IN (SELECT tax_code_id FROM subjournal_report_taxcode_column " \
#        "WHERE report_config_id=%s) ORDER BY code"

        q = "SELECT DISTINCT at.id, at.name, at.code " \
            "FROM account_tax_code at, account_period p, account_move_line l, account_invoice i " \
            "WHERE p.id=l.period_id AND at.id=l.tax_code_id AND p.id=%s " \
            "AND i.type IN %s AND i.move_id=l.move_id " \
            "AND at.id IN (SELECT tax_code_id FROM subjournal_report_taxcode_column " \
            "WHERE report_config_id=%s) ORDER BY at.code"

        #self.cr.execute(q, (self.period_id, tuple(types), self.period_id, tuple(types), config_id))
        self.cr.execute(q, (self.period_id, tuple(types), config_id[0]))
        res = self.cr.fetchall()
        self.columns = res

        ids = map(lambda x: x[0], res)

        res = self.pool.get('account.tax.code').browse(self.cr, self.uid, ids)
        return res

#    def get_columns(self, config_id):
#        # Obtenemos los tax_code que tuvieron movimientos en el periodo pedido
#        types = self._get_types()
#
#        q = "SELECT DISTINCT at.id, at.name, at.code " \
#        "FROM account_tax_code at, account_period p, account_move_line l, account_invoice i " \
#        "WHERE p.id=l.period_id AND at.id=l.tax_code_id AND p.id=%s " \
#        "AND i.type IN %s AND i.move_id=l.move_id " \
#        "AND at.id IN (SELECT tax_code_id FROM subjournal_report_taxcode_column " \
#        "WHERE report_config_id=%s) ORDER BY at.code"
#
#        self.cr.execute(q, (self.period_id, tuple(types), config_id))
#        res = self.cr.fetchall()
#        self.columns = res
#
#        ids = map(lambda x: x[0], res)
#
#        res = self.pool.get('account.tax.code').browse(self.cr, self.uid, ids)
#        return res

    def get_lines(self):
        tax_code_ids = [col[0] for col in self.columns]
        where = ''
        where_param = ()
        if len(tax_code_ids):
            where = " AND tc.id in %s "
            where_param = (tuple(tax_code_ids),)
        types = self._get_types()

        # TODO: Loco!, pero segun la configuracion de Mariano Martene, creo un
        # impuesto que es de 0% llamado IVA Monotributo. Le puso los tax codes correspondientes.
        # Entonces cuando crea una factura para Monotributo (mapea los impuestos en la fiscal_position)
        # Le queda un impuesto con cantidad, pero con base imponible igual al total de la factura (o de
        # los productos que tengan impuestos). Entonces el reporte funciona bien con solo configurarle
        # la columna de la Tax Code correspondiente a la base imponible del Impuesto para Monotributo.
        # TODO Implementar con un select para account_invoice_tax, algo como:
        # Porque sobre algo asi, podemos usar el campo print_total para imprimir
        # el total de la base+impuesto. Aparte queda mas claro que con el Select de mas abajo.
        # select it.id, tc_base.name, it.base_amount, tc_tax.name, it.tax_amount, (it.base_amount+it.tax_amount) as total
        # from account_invoice_tax it, account_invoice i, account_tax_code tc_base,
        # account_tax_code tc_tax
        # where it.invoice_id=i.id and i.id=22 and tc_base.id=it.base_code_id
        # and tc_tax.id=it.tax_code_id

        self.cr.execute("SELECT l.id FROM account_move_line l, account_invoice i, "
                        "account_tax_code tc, account_period ap "
                        "WHERE i.move_id=l.move_id AND tc.id=l.tax_code_id  "
                        "AND i.type IN %s "
                        "AND ap.id=l.period_id AND ap.id=%s "
                        + where + "ORDER BY l.date", (tuple(types), self.period_id) + where_param)

        # Obtenemos el resultado de la consulta
        res = self.cr.fetchall()

        if not len(res):
            raise osv.except_osv(_('Warning'), _('There were no moves for this period'))
            # return res

        # Lineas
        line_ids = map(lambda x: x[0], res)

        account_obj = self.pool.get('account.move.line')
        #ids = account_obj.search(self.cr, self.uid, [('invoice','!=',False), ('tax_code_id','!=',False)])
        lines = {}
        total_invoiced = 0.0
        total_no_taxed = 0.0
        for l in account_obj.browse(self.cr, self.uid, line_ids):
            line = {}

            # Calculamos el signo
            sign = 1
            if l.invoice.type in ('out_refund', 'in_refund'):
                sign = -1

            if not l.move_id.id in lines:
                line['date'] = l.date
                line['partner'] = l.partner_id.name
                line['partner_title'] = l.partner_id.title.name
                line['vat'] = l.partner_id.vat
                line['fiscal_position'] = l.partner_id.property_account_position.name
                line['invoice_type'] = self.get_invoice_type(l.invoice)
#                if l.invoice.type in ('out_invoice', 'out_debit', 'out_refund'):
#                    line['invoice_number'] = '%s-%08d' % (l.invoice.pos_ar_id.name, int(l.invoice.internal_number))
#                else:
#                    line['invoice_number'] = l.invoice.internal_number
                line['invoice_number'] = l.invoice.internal_number
                line['taxes'] = []
                line['taxes'] += [''] * len(tax_code_ids)
                line['no_taxed'] = l.invoice.amount_no_taxed * sign
                line['total'] = l.invoice.amount_total * sign
                total_invoiced += line['total']
                total_no_taxed += line['no_taxed']
                lines[l.move_id.id] = line

            for i, t_id in enumerate(tax_code_ids):
                if l.tax_code_id.id == t_id:
                    if lines[l.move_id.id]['taxes'][i] == '':
                        lines[l.move_id.id]['taxes'][i] = l.tax_amount  # *sign
                    else:
                        lines[l.move_id.id]['taxes'][i] += l.tax_amount  # *sign

        res = [v for k, v in lines.iteritems()]
        res2 = sorted(res, key=lambda k: k['date'])

        line2 = {}
        line2['date'] = ""
        line2['partner'] = ""
        line2['partner_title'] = ""
        line2['vat'] = ""
        line2['fiscal_position'] = ""
        line2['invoice_type'] = ""
        line2['invoice_number'] = ""
        line2['taxes'] = []
        line2['no_taxed'] = total_no_taxed
        line2['total'] = total_invoiced

        # Obtenemos los totales
        tax_sums = self.get_sum()

        line2['taxes'] += [''] * len(tax_code_ids)
        for i, t_id in enumerate(tax_code_ids):
            for tsum_id, sum in tax_sums:
                if t_id == tsum_id:
                    line2['taxes'][i] = sum

        res2.append(line2)
        return res2

    def get_sum(self):
        tax_code_ids = [col[0] for col in self.columns]
        where = ''
        where_param = ()
        if len(tax_code_ids):
            where = " AND tc.id in %s "
            where_param = (tuple(tax_code_ids),)

        types = self._get_types()

        self.cr.execute("SELECT l.tax_code_id, sum(l.tax_amount) as sum_amount "
                        "FROM account_move_line l, account_invoice i,  "
                        "account_tax_code tc, account_period ap "
                        "WHERE i.move_id=l.move_id AND tc.id=l.tax_code_id  "
                        "AND i.type IN %s "
                        "AND ap.id=l.period_id AND ap.id=%s" + where +
                        "GROUP BY l.tax_code_id ORDER BY l.tax_code_id", (tuple(types), self.period_id) + where_param)

        res = self.cr.fetchall()
        return res

    def get_invoice_type(self, inv):
        type = ""
        denomination = ""

        if inv == False:
            return ""

        if inv.type in ('out_invoice', 'in_invoice'):
            if inv.is_debit_note:
                type = "ND"
            else:
                type = "F"
        else:
            type = "NC"

        # TODO: Habria que ver si son comprobantes de Clientes o Proveedores, en lugar de mirar por los campos.
        if inv.pos_ar_id and inv.pos_ar_id.denomination_id:
            denomination = inv.pos_ar_id.denomination_id.name
        elif inv.denomination_id:
            denomination = inv.denomination_id.name

        return '%s %s' % (type, denomination)

    def hello_world(self, name):
        return "Hello, %s!" % name
