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
from openerp.osv import fields, osv
from openerp.tools.translate import _


class account_tax_subjournal(osv.osv_memory):
    _name = "account.tax.subjournal"
    _description = "Account Tax Subjournal Report"

    def _get_report_id(self, cr, uid, context):
        report_id = self.pool.get('ir.actions.report.xml').search(cr, uid, [('report_name', '=', 'account.tax.subjournal')])
        if len(report_id):
            return report_id[0]
        return False

    _columns = {
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal year', help='Keep empty for all open fiscal year', required=True),
        'period': fields.many2one('account.period', 'Period', required=True),
        'report_config_id': fields.many2one('tax.subjournal.report.config', 'Configuration', required=True),
        'report_id': fields.many2one('ir.actions.report.xml', 'Report'),
        'based_on': fields.selection([('sale', 'Sales'),
                                      ('purchase', 'Purchases')], 'Based On', required=True)
    }

    _defaults = {
        'report_id': _get_report_id,
        'based_on': 'sale',
    }

    def create_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'account.move.line'
        datas['form'] = self.read(cr, uid, ids)[0]
        #datas['form']['company_id'] = self.pool.get('account.tax.code').browse(cr, uid, [datas['form']['chart_tax_id']], context=context)[0].company_id.id
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.tax.subjournal',
            'datas': datas,
        }

account_tax_subjournal()
