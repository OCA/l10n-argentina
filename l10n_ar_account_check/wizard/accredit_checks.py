##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import models, api, fields


class WizardAccreditChecks(models.TransientModel):
    _name = 'wizard.accredit.checks'
    _description = 'Select several checks which are Waiting Accreditation so you can accredit them'  # noqa

    @api.model
    def get_default_checks(self):
        check_ids = self.env.context.get("active_ids", [])
        return [(6, False, check_ids)]

    issued_checks = fields.Many2many(
        comodel_name='account.issued.check',
        relation='wiz_accredit_check_rel',
        colum1='wiz_id',
        colum2='check_id',
        default=get_default_checks,
    )

    @api.multi
    def button_accredit_checks(self):
        return self.issued_checks.accredit_checks()
