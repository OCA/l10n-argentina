# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2012 E-MIPS Electronica e Informatica
#                       info@e-mips.com.ar
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
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from openerp.osv import osv, fields


class tax_subjournal_report_config(osv.osv):
    _name = 'tax.subjournal.report.config'
    _description = 'Tax Subjournal Report Configuration'

    _columns = {
        'name': fields.char('Name', size=64),
        'tax_report_id': fields.many2one('ir.actions.report.xml', 'Tax Report', required=True, select=True),
        'tax_column_ids': fields.one2many('subjournal.report.taxcode.column', 'report_config_id', 'Report Columns'),
        'based_on': fields.selection([('sale', 'Sales'),
                                      ('purchase', 'Purchases')], 'Based On', required=True)
    }

    _defaults = {
        'based_on': 'sale',
    }

tax_subjournal_report_config()


class subjournal_report_taxcode_column(osv.osv):
    _name = 'subjournal.report.taxcode.column'
    _description = 'subjournal.report.taxcode.column'

    _columns = {
        'name': fields.char('Name', size=32),
        'report_config_id': fields.many2one('tax.subjournal.report.config', ondelete='cascade'),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax code'),
        'print_total': fields.boolean('Print Total', help="If true, sum  Tax and Base amount. You should use only Tax Code and not Base Code if this is True."),
    }

    # TODO: Como tenemos el campo based_on en el report_config, podriamos
    # filtrar los account_tax_code por los que se aplican a compras, pero
    # esa informacion esta en account_tax.
    # Tal vez, se tenga que quitar la relacion con tax_code_id y hacerlo
    # con account_tax que tiene el campo para diferenciar compras y ventas.
    # De esta manera es mas intuitivo, pero a su vez hay que modificar el
    # codigo de este objeto para agregarle unos booleanos que permitan
    # decidir si se imprime el tax y/o el base de ese account_tax configurado
    # como columna y tambien cambiar el parser.
    # Por ahora, se deja de esta manera, poco intuitivo, pero que funciona
    # correctamente si se configura correctamente.

subjournal_report_taxcode_column()
