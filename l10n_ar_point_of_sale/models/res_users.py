##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    property_default_pos_id = fields.Many2one(
        'pos.ar', string=_('Default POS'),
        help=_('Select the Default Point of Sale'), company_dependent=True)

    @api.multi
    def get_default_pos_id(self, record):
        """
        By default return the default_pos for the user's commercial field
        Otherwise, returns the current user default
        """
        self.ensure_one()
        config_obj = self.env['ir.config_parameter']
        config_param = config_obj.sudo().get_param(
            'default_pos_setting', 'commercial')
        if config_param == 'commercial':
            res = record.user_id.property_default_pos_id
        else:
            res = self.property_default_pos_id
        _logger.info('default_pos({})[{}] for {}: {}'.format(
            config_param, record, self, res))
        return res
