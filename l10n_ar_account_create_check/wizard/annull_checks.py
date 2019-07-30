##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import api, fields, models


class WizardAnnullChecks(models.TransientModel):
    _name = 'wizard.annull.checks'
    _description = 'Wizard to annull checks related to one Checkbook'

    def get_default_checkbook(self):
        return self.env.context.get(
            "active_ids", [self.env.context.get("active_id", False)])[0]

    checkbook_id = fields.Many2one(comodel_name='account.checkbook',
                                   string='Checkbook', required=True,
                                   default=get_default_checkbook)
    checks = fields.Many2many(comodel_name='account.checkbook.check',
                              relation='wizard_annull_checks_rel',
                              column1='wiz_id', column2='check_id',
                              string='Checks', required=True)

    @api.multi
    def button_annull_checks(self):
        self.checks.annull_check()
        state = self.checkbook_id.calc_state()
        return self.checkbook_id.write({"state": state})
