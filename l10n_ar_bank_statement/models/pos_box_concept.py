##############################################################################
#
#    Copyright (C) 2004-2010 Pexego Sistemas Informáticos. All Rights Reserved
#    Copyright (C) 2010-2014 Eynes - Ingeniería del software All Rights Reserved
#    Copyright (c) 2014 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import _, api, exceptions, fields, models


class PoSBoxConcept(models.Model):
    _name = 'pos.box.concept'
    _description = 'Concept with an account to be used by cash.box.in and cash.box.out'

    @api.constrains("code")
    def check_code_not_dup(self):
        for concept in self:
            code = concept.code
            count = self.search_count([("code", "ilike", code)])
            if count > 1:
                raise exceptions.ValidationError(_("Concept duplicated: %s") % code)

    @api.constrains("name", "concept_type")
    def check_name_not_dup(self):
        for concept in self:
            name = concept.name
            count = self.search_count(
                [
                    ("name", "ilike", name),
                    ("concept_type", "=", concept.concept_type),
                ]
            )

            if count > 1:
                raise exceptions.ValidationError(_("Concept duplicated: %s") % name)

    code = fields.Char(string='Code', size=16, required=True)
    name = fields.Char(string='Name', size=128, required=True)
    account_id = fields.Many2one('account.account', string='Account', required=True)
    concept_type = fields.Selection(
        [
            ("in", "Put money in"),
            ("out", "Take money out"),
        ],
        string="Concept type",
        required=True,
    )

class PoSBoxConceptAllowed(models.Model):
    _name = 'pos.box.concept.allowed'
    _description = 'Allow users to see PosBoxConcepts'
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', "Field name must be unique."),
    ]

    name = fields.Char('Name', required=True)
    user_ids = fields.Many2many('res.users', string='Users', required=True)
    concept_ids = fields.Many2many('pos.box.concept', string='PosBox Concepts')

    @api.constrains('user_ids')
    def _check_users(self):
        recordset = self.search([('id', 'not in', self.ids)])
        for record in recordset:
            if set(self.user_ids.ids) & set(record.user_ids.ids):
                raise exceptions.ValidationError(_('Fields users must be unique per model.'))
