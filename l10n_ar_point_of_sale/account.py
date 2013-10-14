# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2008-2011 E-MIPS Electronica e Informatica <info@e-mips.com.ar>
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
from osv import osv, fields

class account_tax(osv.osv):
    _name = 'account.tax'
    _inherit = 'account.tax'
    _description = 'Tax'
    _columns = {
        'tax_group': fields.selection( [('vat','VAT'), ('perception','Perception'), ('retention','Retention'), ('internal','Internal Tax'), ('other','Other')], 'Tax Group', required=True,
            help="This is tax categorization."),
        'other_group': fields.char('Other Group', size=64),
        'is_exempt': fields.boolean('Exempt', help="Check this if this Tax represent Tax Exempts"),
        }

    _defaults = {
            'is_exempt': False,
            'tax_group': 'vat',
            }

account_tax()

class account_move(osv.osv):
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
        return True

account_move()
