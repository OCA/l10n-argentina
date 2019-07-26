##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import \
    serialize_exception, content_disposition


class Binary(http.Controller):
    @http.route('/web/binary/download_document', type='http', auth="public")
    @serialize_exception
    def download_document(self, model, field, id, filename=None, **kw):
        """ Download link for string fields
        :param str model: name of the model to fetch the binary from
        :param str field: binary field
        :param str id: id of the record from which to fetch the binary
        :param str filename: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        """
        Model = request.env[model]
        fields = [field]
        Obj = Model.browse(int(id))
        res = Obj.read(fields)[0]
        filecontent = res.get(field)
        if not filecontent:
            return request.not_found()
        if not filename:
            filename = '%s_%s' % (model.replace('.', '_'), id)
        return request.make_response(
            filecontent,
            [('Content-Type', 'text/plain'),
             ('Content-Disposition', content_disposition(filename))])
