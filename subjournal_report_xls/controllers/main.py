from odoo.addons.web.controllers import main as report
from odoo.tools import html_escape, ustr
from odoo.http import content_disposition, route, request, serialize_exception, Response
from odoo import _
import json

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
