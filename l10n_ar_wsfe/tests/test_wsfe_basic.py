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
from openerp.addons.l10n_ar_wsaa.tests.common import WSAA_Client
from openerp.addons.l10n_ar_wsfe.tests.common import WSFE_Client
from openerp.addons.l10n_ar_wsfe.wsfe_suds import WSFEv1
from openerp import SUPERUSER_ID

class TestWSFE(TransactionCase):

    def setUp(self):
        super(TestWSFE, self).setUp()
        self.wsaa_ta = self.env['wsaa.ta']
        self.wsfe_config = self.env['wsfe.config']

        self.wsaa_demo = self.browse_ref("l10n_ar_wsaa.wsaa_config_demo")
        self.wsfe_demo = self.browse_ref("l10n_ar_wsfe.wsfe_config_demo")
        self.wsaa_service = self.browse_ref("l10n_ar_wsfe.afipws_service_wsfe")
        user = self.env['res.users'].browse(SUPERUSER_ID)
        partner_id = user.partner_id
        partner_id.tz = 'America/Argentina/Buenos_Aires'

        with mock.patch('openerp.addons.l10n_ar_wsaa.wsaa_suds.Client', new=WSAA_Client) as mock_client:
            ta_vals = dict(name=self.wsaa_service.id, config_id=self.wsaa_demo.id)
            self.wsaa_ta = self.wsaa_ta.create(ta_vals)
            self.token, self.sign = self.wsaa_ta.get_token_sign()
            self.wsfe_demo.wsaa_ticket_id = self.wsaa_ta
            self.wsfe_demo.cuit = "30710981295"

    @mock.patch.object(WSFEv1, 'fe_dummy', WSFE_Client.fe_dummy)
    @mock.patch.object(WSFEv1, '_create_client', WSFE_Client._create_client)
    def test_dummy(self):
        res = self.wsfe_demo.get_server_state()
