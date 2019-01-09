# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2014 Noviat nv/sa (www.noviat.com). All rights reserved.
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
##############################################################################

from odoo import models, api


class account_move_line(models.Model):
    _name = 'account.move.line'
    _inherit = 'account.move.line'

    # override list in custom module to add/drop columns or change order
    @api.model
    def _report_xls_fields(self):
        base_lst = [
            'Fecha', 'Razon Social', 'Provincia', 'CUIT', 'Cond. IVA',
            'Tipo', 'Numero', 'No Gravado', 'Total'
        ]
        # base_lst = [
        #     'date', 'partner', 'state', 'vat', 'fiscal_position',
        #     'invoice_type', 'invoice_number', 'no_taxed', 'total'
        # ]
        config_obj = self.env['ir.config_parameter']
        config_param = config_obj.sudo().get_param('subjournal_export_cae')
        if config_param:
            base_lst.insert(6, 'cae')
            base_lst.insert(7, 'cae_due_date')
        return base_lst

    # Change/Add Template entries
    @api.model
    def _report_xls_template(self):
        """
        Template updates, e.g.

        my_change = {
            'move':{
                'header': [1, 20, 'text', _('My Move Title')],
                'lines': [1, 0, 'text', _render("line.move_id.name or ''")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}
