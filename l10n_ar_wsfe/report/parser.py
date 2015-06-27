##############################################################################
#
# Copyright (c) 2008-2010 SIA "KN dati". (http://kndati.lv) All Rights Reserved.
#                    General contacts <info@kndati.lv>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
import random
from datetime import datetime

LINES_PER_PAGE = 18


class Parser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'random': random,
            'hello_world': self.hello_world,
            'invoice_number': self.invoice_number,
            'get_lines': self.get_lines,
            'get_pages': self.get_pages,
            'last_page': self.last_page,
            'get_untaxed': self.get_untaxed,
            'get_taxed': self.get_taxed,
            'get_total': self.get_total,
            'get_doc_code': self.get_doc_code,
            'get_barcode_code': self.get_barcode_code,
        })
        self.total_pages = 0
        self.page_number = 0
        self.untaxed = 0.0
        self.taxed = 0.0
        self.inv_code = '0'

#    def set_context(self, objects, data, ids, report_type=None):
#        super(Parser, self).set_context(objects, data, ids, report_type)

    def hello_world(self, name):
        return "Hello, %s!" % name

    def invoice_number(self, inv):
        return '%s-%s' % (inv.pos_ar_id.name, inv.internal_number)
        # return '0005-%08d' % int(inv_number)

    def _wrap(self, text, n=80):
        text = text.replace('\n', ' ')
        lines = []
        while len(text):
            lines.append(text[:n])
            text = text[n:]

        return lines

    def get_pages(self, inv):
        if self.total_pages == 0:
            line_obj = self.pool.get('account.invoice.line')
            lines_ppage = LINES_PER_PAGE
            if inv.comment:
                comment_lines = self._wrap(inv.comment, 120)
                lines_ppage -= len(comment_lines)

            count = line_obj.search(self.cr, self.uid, [('invoice_id', '=', inv.id)], count=True)
            pages = (count / lines_ppage)
            add = count % lines_ppage
            # print 'Add: ', add, add+LINES_PER_PAGE%LINES_PER_PAGE
            self.remainder_lines = lines_ppage - add
            if add:
                pages = pages + 1
            self.total_pages = pages
        return self.total_pages

    def last_page(self):
        if self.page_number != self.total_pages:
            return xrange(0)
        return xrange(self.remainder_lines)

    def get_lines(self, inv):
        # print 'Denomination: ', inv.denomination_id.name

        # Si la denominacion es B o C, no se discrimina IVA
        vat_disc = inv.denomination_id.vat_discriminated

        line_obj = self.pool.get('account.invoice.line')
        uom_obj = self.pool.get('product.uom')
        limit = LINES_PER_PAGE
        offset = self.page_number * limit
        line_ids = line_obj.search(self.cr, self.uid, [('invoice_id', '=', inv.id)], offset=offset, limit=limit)
        #line_ids = line_obj.search(self.cr, self.uid, [('invoice_id', '=', inv.id)])
        lines = line_obj.browse(self.cr, self.uid, line_ids)
        self.page_number += 1
        ll = []
        for line in lines:
            # Obtenemos la descripcion
            sp = line.name.split(' ')
            try:
                if len(sp) > 1 and sp[0][0] == '[':
                    desc = sp[1:]
                else:
                    desc = line.name
            except:
                desc = line.name

            # Obtenemos lo demas
            code = line.product_id.default_code
            default_uom = line.product_id.uom_id and line.product_id.uom_id.id
            q = uom_obj._compute_qty(self.cr, self.uid, line.uos_id.id, line.quantity, default_uom)
            pu = line.price_unit
            pl = line.product_id.list_price
            discount = line.discount
            discount2 = ((line.product_id.list_price - line.price_unit) * 100) / line.product_id.list_price
            discount2 = round(discount2, 2)

            taxes = line.invoice_line_tax_id
            for tax in taxes:
                # if tax.price_include and tax.type == 'percent':
                if not vat_disc:
                    pu += round(line.price_unit * tax.amount, 4)
                    pl += round(line.product_id.list_price * tax.amount, 4)
                    self.taxed = False
                else:
                    self.taxed = True

            subtotal = round(q * pu * (1 - (line.discount or 0.0) / 100.0), 2)
            self.untaxed += subtotal

            # Para PLOT
            ll.append([code, desc, q, round(pu, 2), discount, discount2, subtotal, round(pl, 2)])
            #ll.append([code, desc, q, pu, discount, discount2, subtotal])

        return ll

    def get_untaxed(self, inv):
        return "%.2f" % self.untaxed

    def get_taxed(self, inv):
        return self.taxed and inv.amount_tax or '0.00'

    def get_total(self, inv):
        return "%.2f" % inv.amount_total

    def get_doc_code(self, inv):
        eivoucher_obj = self.pool.get('wsfe.voucher_type')
        res = eivoucher_obj.search(self.cr, self.uid, [('document_type', '=', inv.type), ('denomination_id', '=', inv.denomination_id.id)])[0]

        ei_voucher_type = eivoucher_obj.browse(self.cr, self.uid, res)
        self.inv_code = ei_voucher_type.code

        return 'Cod. %s' % self.inv_code

    def get_barcode_code(self, inv):
        cuit = inv.company_id.partner_id.vat
        pos = '0005'
        inv_code = self.inv_code
        if inv.state == 'open' and inv.cae != 'NA':
            cae = inv.cae
            cae_due_date = datetime.strptime(inv.cae_due_date, report_sxw.DT_FORMAT)
        else:
            cae_due_date = datetime.now()
            cae = '0' * 14

        code = cuit + '%02d' % int(inv_code) + pos + cae + cae_due_date.strftime('%Y%m%d')
        return code
