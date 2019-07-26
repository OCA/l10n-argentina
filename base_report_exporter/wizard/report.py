##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

import binascii
import logging

from odoo import models, api, fields, _, exceptions

_logger = logging.getLogger(__name__)


class ReportFilesGenerator(models.Model):
    _name = 'report.files.generator'

    exporter_id = fields.Many2one('report.exporter', 'Exporter', required=True)
    exporter_date_type = fields.Selection(
        related='exporter_id.date_type', readonly=True)
    exporter_codename = fields.Char(
        related='exporter_id.codename', readonly=True)
    period_id = fields.Many2one('date.period', string='Period')
    date_start = fields.Date()
    date_stop = fields.Date()
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.user.company_id.id)

    @api.multi
    def get_dates(self):
        if self.exporter_date_type == 'period':
            return (self.period_id.date_from, self.period_id.date_to)
        elif self.exporter_date_type == 'period':
            return (self.date_start, self.date_stop)

    @api.multi
    def do_store(self, state, errors, files):
        report_file_model = self.env['report.files']
        report_file_id = self.env.context.get('report_file_id')
        report_file = report_file_id and report_file_model.browse(
            report_file_id)

        date_start, date_stop = self.get_dates()
        name = '%s [%s -> %s]' % (self.exporter_id.name,
                                  date_start, date_stop)
        _read = self.read()[0]
        values = self._convert_to_write(_read)
        values.update({
            'name': name,
            'state': 'generated' if state else 'error',
        })
        error_values = []
        for err in errors:
            model = err['resource']._name
            oid = err['resource'].id
            resource_str = '%s,%s' % (model, oid)
            error_values.append((0, 0, {
                'resource_ref': resource_str,
                'error': err['error'],
                'type': err.get('type', 'error'),
            }))
        values['error_ids'] = error_values
        if isinstance(report_file, models.BaseModel):
            report_file.attachment_ids.unlink()
            report_file.error_ids.unlink()
            report_file.write(values)
            new_file = report_file
        else:
            new_file = report_file_model.create(values)
        if state:
            for ffile in files:
                f = ffile.get('data')
                try:
                    f.seek(0)
                    data = f.read()
                except Exception:
                    try:
                        data = ("\r\n").join(f)
                    except Exception:
                        data = f
                if isinstance(data, str):
                    data = data.encode('ascii', 'replace')
                encoded_data = binascii.b2a_base64(data)
                data_attach = {
                    'name': ffile.get('name'),
                    'datas_fname': ffile.get('name'),
                    'datas': encoded_data,
                    'res_id': new_file.id,
                    'res_model': 'report.files'
                }
                self.env['ir.attachment'].create(data_attach)
        form_view = self.env.ref('base_report_exporter.view_report_files_form')
        tree_view = self.env.ref('base_report_exporter.view_report_files_tree')
        views = [(form_view.id, 'form'), (tree_view.id, 'tree')]
        return {
            'name': _('Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'report.files',
            'view_type': 'form',
            'view_mode': 'form',
            'views': views,
            'res_id': new_file.id,
        }

    @api.multi
    def postprocess(self, ddict):
        """
        ddict = {
            'state': True|False,
            'errors': [{'resource': recordset, 'error': 'error'}]
            'files': [{'name': 'filename', 'data': IO Buffer}]
        }
        """
        assert isinstance(ddict, dict), 'ddict must be a diktionary'
        state = ddict.get('state')
        errors = ddict.get('errors', [])
        files = ddict.get('files')
        assert isinstance(state, bool), 'state must be boolean'
        assert isinstance(errors, list), 'errors must be a list'
        assert isinstance(files, list), 'files must be a list'
        if state is False:
            assert len(errors) >= 1, 'Expected at least one ' + \
                'error if no success'
        else:
            assert len(files) >= 1, 'Expected at least one file if no errors'
        res = self.do_store(state, errors, files)
        return res

    @api.multi
    def _control_error(self, e):
        _logger.exception('Unable to export %s:\n%s' %
                          (self.exporter_codename, str(e)))
        raise exceptions.ValidationError(
            _('Unable to export. More info in logs.\n' +
              'Error was:\n%s') % str(e))

    @api.multi
    def do_generate(self):
        """
        Calls _do_<exporter_id.codename>
        """
        fname = '_do_%s' % self.exporter_codename
        if not hasattr(self, fname):
            raise exceptions.ValidationError(
                _('Exporter Failure.\n[undefined %s]') % fname)
        # Call function with proper parameter
        fn = getattr(self, fname)
        try:
            res = fn()
        except Exception as e:
            self._control_error(e)

        if not res:
            raise exceptions.ValidationError(
                _("Sorry, there is nothing to export 😢"))
        try:
            end_res = self.postprocess(res)
        except Exception as e:
            self._control_error(e)
        else:
            return end_res
