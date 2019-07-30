##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import api, models, fields


class ResParterBank(models.Model):
    _name = 'res.partner.bank'
    _inherit = 'res.partner.bank'

    @api.multi
    def name_get(self):
        result = []
        for rpb in self:
            name = []
            if rpb.bank_id:
                name.append("[%s]" % rpb.bank_id.name_get()[0][1])
            name.append(rpb.acc_number)
            result.append((rpb.id, " ".join(name)))
        return result

    account_id = fields.Many2one(
        comodel_name='account.account', string='Account')
