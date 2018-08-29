# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2013 Eynes S.R.L. (http://www.eynes.com.ar) All Rights Reserved.
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
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

from odoo import api, fields, models


class WizardAnnullChecks(models.TransientModel):
    _name = 'wizard.annull.checks'
    _description = 'Wizard to annull checks related to one Checkbook'

    def get_default_checkbook(self):
        return self.env.context.get("active_ids", [self.env.context.get("active_id", False)])[0]

    checkbook_id = fields.Many2one('account.checkbook', string='Checkbook', required=True,
                                   default=get_default_checkbook)
    checks = fields.Many2many('account.checkbook.check', 'wizard_annull_checks_rel', 'wiz_id',
                              'check_id', string='Checks', required=True)

    @api.multi
    def button_annull_checks(self):
        self.checks.annull_check()
        state = self.checkbook_id.calc_state()
        return self.checkbook_id.write({"state": state})
