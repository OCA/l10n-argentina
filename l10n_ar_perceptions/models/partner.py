###############################################################################
#
#    Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import models, fields, api


class ResPartnerPerception(models.Model):
    _name = "res.partner.perception"
    _description = "Perception Defined in Partner"
    _rec_name = 'perception_id'

    perception_id = fields.Many2one('perception.perception', 'Perception',
                                    required=True)
    # FIXME: Old definition was related(char).
    # perception_type = fields.Selection(string='Perception Type',
    #                                    related='perception_id.type')
    activity_id = fields.Many2one('perception.activity', 'Activity')
    percent = fields.Float('Percent', required=True)
    excluded_percent = fields.Float('Percentage of Exclusion')
    ex_date_from = fields.Date('From date')
    ex_date_to = fields.Date('To date')
    exclusion_certificate = fields.Binary(string='Exclusion Certificate')
    partner_id = fields.Many2one('res.partner', 'Partner')
    sit_iibb = fields.Many2one(comodel_name='iibb.situation',
                               string='Situation of IIBB')

    _sql_constraints = [('perception_partner_unique',
                         'unique(partner_id, perception_id)',
                         'There must be only one perception of this ' +
                         'type configured for the partner')]

    @api.onchange('perception_id')
    def perception_id_change(self):
        perception_type = self.perception_id.type
        domain = [('type', '=', perception_type)]
        return {'domain': {'activity_id': domain}}


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    perception_ids = fields.One2many(
        'res.partner.perception', 'partner_id', 'Defined Perceptions',
        help="Here you have to configure perception exceptions for this " +
        "partner with this Fiscal Position")
    nro_insc_iibb = fields.Char('Number of IIBB Registration', size=15)

    def _get_perceptions_to_apply(self):

        # Buscamos las percepciones a aplicar segun la posicion fiscal
        # partner = self.browse(cr, uid, partner_id, context)
        perceptions = {}
        for perc in self.property_account_position.perception_ids:
            perception = {
                'perception': perc,
                'activity_id': False,
                'excluded_percent': False,
                'percent': -1.0,
                'ex_date_to': False,
                'ex_date_from': False,
                'sit_iibb': False,
                'from_padron': False,
            }

            perceptions[perc.id] = perception

        # Ahora buscamos a ver si tiene alguna excepcion
        partner_perceptions = {}
        for p_perc in self.perception_ids:

            perception = {
                'perception': p_perc.perception_id,
                'activity_id': p_perc.activity_id.id,
                'excluded_percent': p_perc.excluded_percent,
                'percent': p_perc.percent,
                'ex_date_to': p_perc.ex_date_to,
                'ex_date_from': p_perc.ex_date_from,
                'sit_iibb': p_perc.sit_iibb,
                'from_padron': p_perc.from_padron,
            }

            partner_perceptions[p_perc.perception_id.id] = perception

        # Actualizamos el diccionario de retenciones
        perceptions.update(partner_perceptions)
        return perceptions


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    perception_ids = fields.Many2many(
        'perception.perception', 'fiscal_position_perception_rel',
        'position_id', 'perception_id', 'Perceptions',
        help="These are the perceptions that will be applied to Suppliers " +
        "belonging to this Fiscal Position. Exceptions to this have to be " +
        "loaded at partner form.")
