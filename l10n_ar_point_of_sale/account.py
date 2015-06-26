# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012-2014 E-MIPS (http://www.e-mips.com.ar)
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

from openerp import models, fields, _
from openerp.osv import osv

class account_tax(models.Model):
    _name = 'account.tax'
    _inherit = 'account.tax'
    _description = 'Tax'

    tax_group = fields.Selection( [('vat','VAT'),
                                   ('perception','Perception'),
                                   ('retention','Retention'),
                                   ('internal','Internal Tax'),
                                   ('other','Other')], string='Tax Group', default='vat', required=True, help="This is tax categorization.")
    other_group = fields.Char(string='Other Group', size=64)
    is_exempt = fields.Boolean(string='Exempt', default=False, help="Check this if this Tax represent Tax Exempts")


class account_move(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    # Heredamos para que no ponga el nombre del internal_number
    # al asiento contable, sino que siempre siga la secuencia
    def post(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        valid_moves = self.validate(cr, uid, ids, context)

        if not valid_moves:
            raise osv.except_osv(_('Integrity Error !'), _('You can not validate a non-balanced entry !\nMake sure you have configured payment terms properly !\nThe latest payment term line should be of the type "Balance" !'))
        obj_sequence = self.pool.get('ir.sequence')
        for move in self.browse(cr, uid, valid_moves, context=context):
            if move.name =='/':
                new_name = False
                journal = move.journal_id

                if journal.sequence_id:
                    c = {'fiscalyear_id': move.period_id.fiscalyear_id.id}
                    new_name = obj_sequence.next_by_id(cr, uid, journal.sequence_id.id, c)
                else:
                    raise osv.except_osv(_('Error'), _('No sequence defined on the journal !'))

                if new_name:
                    self.write(cr, uid, [move.id], {'name':new_name})

        cr.execute('UPDATE account_move '\
                   'SET state=%s '\
                   'WHERE id IN %s',
                   ('posted', tuple(valid_moves),))
        self.invalidate_cache(cr, uid, context=context)
        return True

account_move()
