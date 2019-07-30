##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

import logging

from odoo import models, api, fields, _

_logger = logging.getLogger(__name__)


class ReportExporter(models.Model):
    _name = 'report.exporter'
    _description = 'Report Exporter'

    DATE_TYPES = [('period', 'Period'), ('date', 'Dates')]

    def _default_groups(self):
        return self.env.ref('account.group_account_manager',
                            raise_if_not_found=False)

    name = fields.Char(required=True)
    codename = fields.Char(required=True, readonly=True)
    date_type = fields.Selection(
        selection=DATE_TYPES, required=True, default='period')
    group_ids = fields.Many2many(
        'res.groups', string='Groups', default=_default_groups)
    related_ui_ids = fields.Many2many('ir.model.data')

    @api.multi
    def _register_hook(self):
        res = super()._register_hook()
        records = self.search([])
        _logger.info("Generating Exporter Menus")
        for rec in records:
            rec.refresh_ui_stuff()
        return res

    @api.multi
    def refresh_ui_stuff(self):
        """
        Prepares the menues and actions.
        """
        if self._context.get('no_ui_update'):
            return
        self.ensure_one()
        basename = 'base_report_exporter'

        # Actw wizard of exporter
        exporter_act_window_id = '%s.action_rfg_%s_exporter' % (
            basename, self.codename)
        ctx_in_act = {
            'default_exporter_id': self.id,
        }
        exporter_aw_values = {
            'model': 'ir.actions.act_window',
            'id': exporter_act_window_id,
            'name': self.name + _(' Exporter'),
            'res_model': 'report.files.generator',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx_in_act.__str__(),
        }
        self.create_or_update(exporter_aw_values)

        # Main menu for this exporter
        main_menu_id = '%s.menu_rfg_%s_main' % (basename, self.codename)
        main_menu_values = {
            'model': 'ir.ui.menu',
            'id': main_menu_id,
            'name': self.name,
            'parent_id': 'base_report_exporter.menu_parent_exporters',
        }
        self.create_or_update(main_menu_values)

        # Menu of wizard & associate it
        exporter_menu_id = '%s.menu_rfg_%s_exporter' % (
            basename, self.codename)
        generator_menu_values = {
            'model': 'ir.ui.menu',
            'id': exporter_menu_id,
            'name': self.name + _(' Exporter'),
            'parent_id': '%s' % main_menu_id,
            'action': exporter_act_window_id,
        }
        self.create_or_update(generator_menu_values)

        # Actw for viewing the reports
        view_act_window_id = '%s.action_rfg_%s_view_reports' % (
            basename, self.codename)
        ctx_in_act = {}
        view_aw_values = {
            'model': 'ir.actions.act_window',
            'id': view_act_window_id,
            'name': self.name + _(' Reports'),
            'res_model': 'report.files',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('exporter_id', '=', self.id)],
            'context': ctx_in_act.__str__(),
        }
        self.create_or_update(view_aw_values)

        # Menu for viewing the reports & associate it
        exporter_menu_id = '%s.menu_rfg_%s_reports' % (basename, self.codename)
        generator_menu_values = {
            'model': 'ir.ui.menu',
            'id': exporter_menu_id,
            'name': self.name + _(' Reports'),
            'parent_id': '%s' % main_menu_id,
            'action': view_act_window_id,
        }
        self.create_or_update(generator_menu_values)

    @api.multi
    def create_or_update(self, values):
        """{'id': 'fq extid', 'model': 'ir.ui.view'}"""
        assert 'model' in values, 'model must be in values'
        assert 'id' in values, 'external_id is required'
        external_id = values.pop('id')
        model = values.pop('model')
        # Search the object
        obj = self.env.ref(external_id, raise_if_not_found=False)
        if 'parent_id' in values:
            values['parent_id'] = self.env.ref(values.get('parent_id')).id
            # ^-- get the object based on the string
        if 'action' in values:
            live_obj = self.env.ref(values.get('action'))
            ref_text = '%s,%s' % (live_obj._name, live_obj.id)
            values['action'] = ref_text
            # ^-- get the object based on the string
        if obj:
            obj.write(values)
        else:
            obj_model = self.env[model]
            obj = obj_model.create(values)
            # Generate imd data
            imd_obj = self.env['ir.model.data']
            module, name = external_id.split('.')
            imd_rec = imd_obj.create({
                'model': obj_model._name,
                'name': name,
                'module': module,
                'res_id': obj.id,
            })
            self.with_context(no_ui_update=True).write({
                'related_ui_ids': [(4, imd_rec.id, 0)],
            })

    @api.model
    def create(self, values):
        res = super().create(values)
        res.refresh_ui_stuff()
        return res

    @api.multi
    def write(self, values):
        res = super().write(values)
        for rec in self:
            rec.refresh_ui_stuff()
        return res

    @api.multi
    def unlink(self):
        tounlink_also = self.related_ui_ids
        res = super().unlink()
        _logger.warning('Unlinking %s' % tounlink_also)
        for imd in tounlink_also:
            model, oid = imd.model, imd.res_id
            self.env[model].browse(oid).unlink()
        return res


class ReportFiles(models.Model):
    _inherit = 'report.files.generator'
    _name = 'report.files'
    _description = 'Exported Files'

    STATES = [
        ('error', 'Error'),
        ('generated', 'Generated'),
        ('declared', 'Declared')]

    name = fields.Char(required=True)

    state = fields.Selection(selection=STATES, required=True)
    error_ids = fields.One2many(
        'report.files.error', 'file_id', string='Errors')
    attachment_ids = fields.One2many(
        'ir.attachment', compute='_compute_attachment_ids',
        string="Attachments")

    @api.multi
    def _compute_attachment_ids(self):
        for x in self:
            x.attachment_ids = self.env['ir.attachment'].search([
                ('res_id', '=', x.id),
                ('res_model', '=', 'report.files')]).ids

    @api.multi
    def to_declared(self):
        self.write({'state': 'declared'})

    @api.multi
    def to_generated(self):
        self.write({'state': 'generated'})

    @api.multi
    def regenerate(self):
        for rec in self:
            rec.with_context(report_file_id=rec.id).do_generate()
        return True


class ReportFilesError(models.Model):
    _name = 'report.files.error'
    _description = 'Errors for an exportat'

    resource_ref = fields.Char(required=True)
    resource_name = fields.Char(compute='_get_name')
    error = fields.Text(required=True)
    file_id = fields.Many2one('report.files', required=True)
    type = fields.Selection([
        ('error', 'Error'),
        ('warning', 'Warning'),
    ], string="Type", default='error')

    @api.multi
    def goto(self):
        model, oid = self.resource_ref.split(',')
        res = {
            'name': self.error,
            'type': 'ir.actions.act_window',
            'res_model': model,
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': int(oid),
        }
        return res

    @api.multi
    def _get_name(self):
        for error in self:
            model, oid_str = error.resource_ref.split(',')
            oid = int(oid_str)
            obj = self.env[model].browse(oid)
            name = obj.display_name
            error.resource_name = '[%s] %s' % (model, name)
