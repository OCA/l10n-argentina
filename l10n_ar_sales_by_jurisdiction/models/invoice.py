###############################################################################
#   Copyright (c) 2019 E-MIPS/Eynes
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
###############################################################################

from odoo import models, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # allow inherited modules to extend the query
    @api.multi
    def _report_xls_query_extra(self):
        select_extra = """ """
        join_extra = """ """
        where_extra = """ """
        sort_selection = """ """
        return (select_extra, join_extra, where_extra, sort_selection)
