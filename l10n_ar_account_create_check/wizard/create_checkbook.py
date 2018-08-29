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

from odoo import fields, models, _
from odoo.exceptions import UserError


class WizardCreateCheck(models.Model):
    _name = "wizard.create.check"
    _description = "wizard create check"

    bank_account_id = fields.Many2one('res.partner.bank', 'Bank', required=True)
    start_num = fields.Char('Start number of check', size=20, required=True)
    end_num = fields.Char('End number of check', size=20, required=True)
    checkbook_num = fields.Char('Checkbook number', size=20, required=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 required=True,
                                 default=lambda self: self.env.user.company_id.id)
    type = fields.Selection([('common', 'Common'), ('postdated', 'Post-dated')], 'Checkbook Type', help="If common, checks only have issued_date. If post-dated they also have payment date", required=True)

    def create_checkbook(self):
        checkbook_obj = self.env['account.checkbook']
        checkbook_id = False
        __import__('ipdb').set_trace()
        for form in self:
            start_num = int(form.start_num)
            end_num = int(form.end_num)
            if start_num > end_num:
                raise UserError(_('Error creating Checkbook!\nEnd number cannot be lower than Start number'))

            # Creamos los cheques numerados
            checks = []
            for n in range(start_num, end_num + 1):
                check_vals = {'name': str(n), 'type': form.type}
                checks.append((0, 0, check_vals))

            # Creamos la chequera
            checkbook_vals = {
                'name': form.checkbook_num,
                'bank_id': form.bank_account_id.bank_id.id,
                'bank_account_id': form.bank_account_id.id,
                'check_ids': checks,
                'type': form.type,
            }

            checkbook_id = checkbook_obj.create(checkbook_vals)

        if not checkbook_id:
            return {'type': 'ir.actions.act_window_close'}

        return {
            'domain': [('id', '=', str(checkbook_id.id))],
            'name': 'Checkbook',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.checkbook',
            'view_id': False,
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window'
        }
