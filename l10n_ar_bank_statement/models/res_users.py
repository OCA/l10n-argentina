##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from openerp import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.multi
    def get_pbc_ids(self):
        """
        Get PosBoxConcepts that are asociated with this user.
        """
        self.ensure_one()
        pbc_lst = self.env['pos.box.concept'].search([]).ids
        allowed_pbc = self.env['pos.box.concept.allowed'].search([])
        for apbc in allowed_pbc:
            if self.id in apbc.user_ids.ids:
                pbc_lst = apbc.concept_ids.ids
        return pbc_lst
