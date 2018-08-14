# -*- coding: utf-8 -*-
##############################################################################

#   Copyright (c) 2018 E-MIPS / Eynes (Martín Nicolás Cuesta)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

##############################################################################


import logging

from odoo.addons.l10n_ar_wsfe.tests.setup_tests import TestSetUp

_logger = logging.getLogger(__name__)


class ConnectorInvoice(TestSetUp):

    def test_a01_asynchronicity(self):
        inv1 = self.create_invoice()
        inv2 = self.create_invoice()
        inv3 = self.create_invoice()
        inv1.signal_workflow('invoice_open')
        inv2.signal_workflow('invoice_open')
        inv3.signal_workflow('invoice_open')
        # Tests not available with workers :'(
