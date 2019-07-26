##############################################################################
#   Copyright (c) 2018 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

import base64
from datetime import datetime
import logging
import os

import xlrd

from odoo import api, fields, models
from odoo.tools import config

log_level_option = config.get("log_level")
loggername = 'openerp.addons.pentaho_auto_prpt'
log_handlers = config.get('log_handler')
handler_levels = dict(handler.split(':') for handler in log_handlers)
default_loglevel = config._LOGLEVELS.get(log_level_option)

data_dir = config.get("data_dir")
data_dir = os.path.isdir(data_dir) and data_dir or os.path.dirname(__file__)

try:
    level_name = handler_levels[loggername]
    loglevel = getattr(logging, level_name)
except (KeyError, AttributeError):
    loglevel = default_loglevel

_logger = logging.getLogger(loggername)
try:
    _logger.setLevel(loglevel)
except TypeError:
    pass


class WizardImportAccountBankStatementLine(models.TransientModel):
    _name = "wizard.import.account.bank.statement.line"
    _description = "Wizard to import Account Bank " + \
        "Statement Lines from a spreadsheet"

    filename = fields.Char('Filename')
    filedata = fields.Binary('File', required=True)
    statement_id = fields.Many2one(
        'account.bank.statement',
        string='Statement',
        required=True,
        ondelete='cascade',
        default=lambda w: w._get_default_statement_id(),
    )

    _code_concept_map = {}

    def _get_default_statement_id(self):
        wiz_model = self.env["wizard.add.account.bank.statement.line"]
        return wiz_model._get_default_statement_id()

    def save_file(self, name, value):
        name, extension = os.path.splitext(name)
        name = datetime.today().strftime(
            "{}_%H%M%S-%d%m%y{}".format(name, extension))

        base_path = os.path.join(
            data_dir, "imported_account_bank_statement_line",)
        if not os.path.isdir(base_path):
            os.mkdir(base_path)

        path = os.path.join(base_path, name)
        with open(path, 'wb+') as new_file:
            new_file.write(base64.decodestring(value))

        _logger.debug("Save file in: %s", path)
        return path

    def find_concept_by_code(self, code):
        concept = concept_obj = self.env["pos.box.concept"]
        if code in self._code_concept_map:
            concept = self._code_concept_map[code]

        if not concept:
            concept = concept_obj.search([("code", "ilike", code)])

        self._code_concept_map[code] = concept

        return concept

    def _prepare_statement_line_data(self, row, statement):
        code = row[0]
        concept = self.find_concept_by_code(code)
        if concept:
            ref = row[1]
            amount = row[2]
            try:
                date = row[3]
            except IndexError:
                date = fields.Date.today()

            line_type = concept.concept_type
            if line_type == "out" and amount > 0:
                amount = -amount

            return {
                "ref": ref,
                "amount": amount,
                "date": date,
                "line_type": line_type,
                "journal_id": statement.journal_id.id,
                "name": concept.name,
                "account_id": concept.account_id.id,
                "state": "confirm",
            }

    def _build_line_ids(self, sheet):
        line_ids = []
        statement = self.statement_id
        for row_number in range(sheet.nrows):
            row_values = sheet.row_values(row_number)
            line_data = self._prepare_statement_line_data(
                row_values, statement)
            if not line_data:
                continue

            line_ids.append((0, False, line_data))

        return line_ids

    @api.multi
    def process_file(self):
        _logger.info("Start prices importation")
        path = self.save_file(self.filename, self.filedata)

        with xlrd.open_workbook(path) as book:
            sheet = book.sheets()[0]
            _logger.debug("Using sheet: %s", sheet.name)

            line_ids = self._build_line_ids(sheet)
            self.statement_id.write({"line_ids": line_ids})

    @api.multi
    def button_process_file(self):
        return self.process_file()
