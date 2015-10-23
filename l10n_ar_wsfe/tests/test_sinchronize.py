# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2015 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2015 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
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

import mock
import time
import unittest2
from openerp.tests.common import TransactionCase
from openerp.addons.l10n_ar_wsfe.tests.common import WSFE_Client, \
                                                     WSFE_ConfigTest, \
                                                     test_invoices
from openerp.addons.l10n_ar_wsfe.wsfe_suds import WSFEv1
from openerp.addons.l10n_ar_wsfe.wsfe import wsfe_config

class TestWSFE(TransactionCase):

    def create_invoice(self, partner_id, price_unit):

        invoice = self.invoice_model.create(dict(
            partner_id=partner_id,
            reference_type='none',
            currency_id=self.currency_ars.id,
            name='invoice to client',
            account_id=self.account_rcv.id,
            type='out_invoice',
            date_invoice=time.strftime('%Y-%m-%d')))

        self.invoice_line_model.create(dict(
            product_id=self.product.id,
            quantity=1,
            price_unit=price_unit,
            invoice_id=invoice.id,
            name='product test'))

        res = invoice.onchange_partner_id('out_invoice', partner_id)
        invoice.write(res['value'])

        test_invoices[invoice.id] = invoice
        return invoice

    def setUp(self):
        super(TestWSFE, self).setUp()
        self.wsfe_config = self.env['wsfe.config']
        self.invoice_model = self.env['account.invoice']
        self.invoice_line_model = self.env['account.invoice.line']
        self.wizard_sinchro = self.env['wsfe.sinchronize.voucher']
        self.wizard_massive_sinchro = self.env['wsfe.massive.sinchronize']
        self.voucher_invoice_A = self.browse_ref("l10n_ar_wsfe.voucher_invoice_A")
        self.pos_demo = self.browse_ref("l10n_ar_wsfe.wsfe_pos_A0001_demo")
        self.pos_demo0 = self.browse_ref("l10n_ar_point_of_sale.point_of_sale_0001A")

        self.partner_asustek = self.browse_ref("base.res_partner_1")
        self.partner_agrolait = self.browse_ref("base.res_partner_2")
        self.partner_china_export = self.browse_ref("base.res_partner_3")
        self.currency_ars = self.browse_ref("base.ARS")
        self.account_rcv = self.browse_ref("account.a_recv")
        self.product = self.browse_ref("product.product_product_4")
        test_invoices.clear()

    @mock.patch.object(WSFEv1, '_create_client', WSFE_Client._create_client)
    @mock.patch.object(wsfe_config, 'get_last_voucher', WSFE_ConfigTest.get_last_voucher)
    @mock.patch.object(wsfe_config, 'get_invoice_CAE', WSFE_ConfigTest.get_invoice_CAE_approved)
    @mock.patch.object(wsfe_config, 'get_voucher_info', WSFE_ConfigTest.get_voucher_info)
    def test_01_voucher_sinchronize(self):
        """Testeamos la sincronizacion masiva."""
        # Validamos alguna factura
        invoice1 = self.create_invoice(self.partner_agrolait.id, 300)
        invoice1.signal_workflow('invoice_open')
        invoice2 = self.create_invoice(self.partner_agrolait.id, 400)
        invoice2.signal_workflow('invoice_open')
        invoice3 = self.create_invoice(self.partner_agrolait.id, 500)

        wiz1 = self.wizard_sinchro.create(dict(
                                voucher_type=self.voucher_invoice_A.id,
                                voucher_number=3,
                                pos_id=self.pos_demo.id))
        wiz1.change_pos()
        wiz1.change_voucher_number()

        # Asserteamos algunas cositas
        self.assertTrue(wiz1.invoice_id)
        draft_invoices = filter(lambda x: x.state=='draft', test_invoices.values())
        invoice = draft_invoices[0]

        self.assertEquals(wiz1.invoice_id.id, invoice.id)
        self.assertEquals(wiz1.invoice_id.state, 'draft')

        # Relacionamos la factura
        wiz1.relate_invoice()

        # Y ahora tiene que estar Open
        self.assertEquals(wiz1.invoice_id.state, 'open')

    @mock.patch.object(WSFEv1, '_create_client', WSFE_Client._create_client)
    @mock.patch.object(wsfe_config, 'get_last_voucher', WSFE_ConfigTest.get_last_voucher)
    @mock.patch.object(wsfe_config, 'get_invoice_CAE', WSFE_ConfigTest.get_invoice_CAE_approved)
    @mock.patch.object(wsfe_config, 'get_voucher_info', WSFE_ConfigTest.get_voucher_info)
    def test_02_voucher_massive_sinchronize(self):

        # Validamos alguna factura
        invoice1 = self.create_invoice(self.partner_agrolait.id, 400)
        invoice1.signal_workflow('invoice_open')

        invoice2 = self.create_invoice(self.partner_agrolait.id, 300)
        invoice3 = self.create_invoice(self.partner_agrolait.id, 300)
        invoice4 = self.create_invoice(self.partner_asustek.id, 400)
        invoice5 = self.create_invoice(self.partner_asustek.id, 300)

        # Asserteamos datos
        self.assertEquals(len(test_invoices), 5)
        draft_invoices = filter(lambda x: x.state=='draft', test_invoices.values())
        self.assertEquals(len(draft_invoices), 4)

        wiz1 = self.wizard_massive_sinchro.create(dict(
                                voucher_type=self.voucher_invoice_A.id,
                                pos_id=self.pos_demo.id))

        # Sincronizamos
        wiz1.with_context(commit=False).sinchronize()

        draft_invoices = filter(lambda x: x.state=='draft', test_invoices.values())
        self.assertEquals(len(draft_invoices), 1)
