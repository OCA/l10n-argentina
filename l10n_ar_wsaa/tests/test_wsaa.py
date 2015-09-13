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
import common
from openerp.tests.common import TransactionCase
from openerp import SUPERUSER_ID

class TestWSAA(TransactionCase):

    def setUp(self):
        super(TestWSAA, self).setUp()
        self.wsaa_config = self.env['wsaa.config']
        self.wsaa_ta = self.env['wsaa.ta']

        self.wsaa_demo = self.browse_ref("l10n_ar_wsaa.wsaa_config_demo")
        self.wsaa_service = self.browse_ref("l10n_ar_wsaa.afipws_service_wsaa_test")
        user = self.env['res.users'].browse(SUPERUSER_ID)
        partner_id = user.partner_id
        partner_id.tz = 'America/Argentina/Buenos_Aires'

    def test_authentication(self):

        ta_vals = dict(name=self.wsaa_service.id, config_id=self.wsaa_demo.id)
        wsaa_ta = self.wsaa_ta.create(ta_vals)

        with mock.patch('openerp.addons.l10n_ar_wsaa.wsaa_suds.Client', new=common.WSAA_Client) as mock_client:
            suds_service = wsaa_ta.get_token_sign()
            self.assertEquals(len(suds_service), 2)
            self.assertEquals(suds_service[0], 'token_test')
            self.assertEquals(suds_service[1], 'sign_test')
