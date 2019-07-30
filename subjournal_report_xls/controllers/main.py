##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

import json

from odoo.addons.web.controllers import main as report
from odoo.tools import html_escape
from odoo.http import route, request, serialize_exception
from odoo import _


class ReportController(report.ReportController):
    @route()
    def report_routes(self, reportname, docids=None, converter=None, **data):
        try:
            res = super(ReportController, self).report_routes(
                reportname, docids, converter, **data
            )
        except Exception as e:
            error = {
                    'code': 200,
                    'message': _("Report error"),
                    'data': serialize_exception(e)
            }
            res = request.make_response(html_escape(json.dumps(error)))
        return res
