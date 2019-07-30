##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import models, fields


class AgipRetentionGroup(models.Model):
    _name = 'agip.retention.group'
    _description = 'Group number of Retention'

    name = fields.Char('Group Number', size=2, index=1)
    aliquot = fields.Float("Aliquot", digits=(3, 2))


class AgipPerceptionGroup(models.Model):
    _name = 'agip.perception.group'
    _description = 'Group number of Perception'

    name = fields.Char('Group Number', size=2, index=1)
    aliquot = fields.Float("Aliquot", digits=(3, 2))


class AgipRetentions(models.Model):
    """
    This model represent the agip csv file that defines percentage
    of retentions and perceptions
    """
    _name = 'padron.agip_percentages'
    _description = 'Definition of percentages of taxes by customer'

    from_date = fields.Date('From date')
    to_date = fields.Date('To date')
    vat = fields.Char('Afip code', size=15, index=1)
    percentage_perception = fields.Float('Percentage of perception')
    percentage_retention = fields.Float('Percentage of retention')
    multilateral = fields.Boolean('Is multilateral?')
    name_partner = fields.Text('Company name')
    group_retention_id = fields.Many2one(
        'agip.retention.group', 'Retention Group')
    group_perception_id = fields.Many2one(
        'agip.perception.group', 'Perception Group')


class ArbaPerceptions(models.Model):
    """
    This model represent de ARBA csv file that
    defines percentage of perceptions
    """
    _name = 'padron.arba_perception'
    _description = 'Definition of arba percentages of perception'

    from_date = fields.Date('From date')
    to_date = fields.Date('To date')
    vat = fields.Char('Afip code', size=15, index=1)
    percentage = fields.Float('Percentage of perception')
    multilateral = fields.Boolean('Is multilateral?')


class ArbaRetentions(models.Model):
    """
    This model represent de ARBA csv file that
    defines percentage of retention
    """
    _name = 'padron.arba_retention'
    _description = 'Definition of arba percentages of retention'

    from_date = fields.Date('From date')
    to_date = fields.Date('To date')
    vat = fields.Char('Afip code', size=15, index=1)
    percentage = fields.Float('Percentage of retention')
    multilateral = fields.Boolean('Is multilateral?')
