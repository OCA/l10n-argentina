# -*- coding: utf-8 -*-
##############################################################################

#   Copyright (c) 2018 E-MIPS / Eynes (Martín Nicolás Cuesta)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

##############################################################################


from odoo.tests.common import TransactionCase

import logging
import time

_logger = logging.getLogger(__name__)

translate_logger = logging.getLogger('openerp.tools.translate')
translate_logger.setLevel('INFO')


class TestSetUp(TransactionCase):
    """
    General SetUp Class for all the tests of the `l10n_ar_wsfe` module.
    """

    def tearDown(self):
        super(TestSetUp, self).tearDown()

    def setUp(self):
        super(TestSetUp, self).setUp()
        self.currency = self.browse_ref("base.ARS")
        self.env.user.company_id.write({'currency_id': self.currency.id})

        self.period_model = self.env['account.period']
        self.move_model = self.env['account.move']
        self.invoice_model = self.env['account.invoice']
        self.account_model = self.env['account.account']
        self.partner_model = self.env['res.partner']
        # self.connector_model = self.env['

        self.today = time.strftime("%Y-%m-%d")
        self.period_id = self.period_model.find(self.today)
        self.account = self.account_model.search([('type', '=', 'other')],
                                                 limit=1)[0]

        self.partner1 = self.partner_model.search([('is_company', '=', True),
                                                  ('customer', '=', True)],
                                                  limit=1)[0]

    def create_invoice(self):
        inv_line_vals = {
            'account_id': self.account.id,
            'name': 'Test Line',
            'price_unit': 100,
            'quantity': 1,
        }
        inv_vals = {
            'account_id': self.account.id,
            'partner_id': self.partner1.id,
            'invoice_line_ids': [(0, 0, inv_line_vals)],
        }
        inv = self.invoice_model.create(inv_vals)
        return inv
