##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import base64

from odoo import _, fields, models

base64.encodestring = base64.encodebytes


class AccountVatLedger(models.Model):

    _name = "account.vat.ledger"
    _description = "Account VAT Ledger"
    _inherit = ["mail.thread"]
    _order = "date_from desc"

    digital_skip_invoice_tests = fields.Boolean(
        string="Skip invoice test?",
        help="If you skip invoice tests probably you will have errors when "
        "loading the files in digital.",
    )
    digital_skip_lines = fields.Char(
        string="Lines list to skip with digital files",
        help="Enter a list of lines, for eg '1, 2, 3'. If you skip some lines "
        "you would need to enter them manually",
    )
    REGDIGITAL_CV_ALICUOTAS = fields.Text(
        "REGDIGITAL_CV_ALICUOTAS",
        readonly=True,
    )
    REGDIGITAL_CV_COMPRAS_IMPORTACIONES = fields.Text(
        "REGDIGITAL_CV_COMPRAS_IMPORTACIONES",
        readonly=True,
    )
    REGDIGITAL_CV_CBTE = fields.Text(
        "REGDIGITAL_CV_CBTE",
        readonly=True,
    )
    REGDIGITAL_CV_CABECERA = fields.Text(
        "REGDIGITAL_CV_CABECERA",
        readonly=True,
    )
    digital_vouchers_file = fields.Binary(
        "Digital Voucher File", compute="_compute_digital_files", readonly=True
    )
    digital_vouchers_filename = fields.Char(
        "Digital Voucher Filename",
        compute="_compute_digital_files",
    )
    digital_aliquots_file = fields.Binary(
        "Digital Aliquots File", compute="_compute_digital_files", readonly=True
    )
    digital_aliquots_filename = fields.Char(
        "Digital Aliquots Filename",
        readonly=True,
        compute="_compute_digital_files",
    )
    digital_import_aliquots_file = fields.Binary(
        "Digital Import Aliquots File", compute="_compute_digital_files", readonly=True
    )
    digital_import_aliquots_filename = fields.Char(
        "Digital Import Aliquots File",
        readonly=True,
        compute="_compute_digital_files",
    )
    prorate_tax_credit = fields.Boolean("Prorate Tax Credit")

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=lambda self: self.env["res.company"]._company_default_get(
            "account.vat.ledger"
        ),
    )
    type = fields.Selection(
        [("sale", "Sale"), ("purchase", "Purchase")], "Type", required=True
    )
    date_from = fields.Date(
        string="Date From",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    journal_ids = fields.Many2many(
        "account.journal",
        "account_vat_ledger_journal_rel",
        "vat_ledger_id",
        "journal_id",
        string="Journals",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    presented_ledger = fields.Binary(
        "Presented Ledger",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    presented_ledger_name = fields.Char("Presented Ledger Name")
    state = fields.Selection(
        [("draft", "Draft"), ("presented", "Presented"), ("cancel", "Cancelled")],
        "State",
        required=True,
        default="draft",
    )
    note = fields.Html("Note")

    name = fields.Char("Name", compute="_compute_name")
    reference = fields.Char("Reference")
    invoice_ids = fields.Many2many(
        "account.move", string="Invoices", compute="_compute_data"
    )

    def _compute_data(self):
        if self.type == "sale":
            invoices_domain = [
                ("state", "not in", ["draft", "cancel"]),
                ("document_number", "!=", False),
                ("journal_id", "in", self.journal_ids.ids),
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
            ]
            invoices = self.env["account.move"].search(
                invoices_domain, order="invoice_date asc, document_number asc, id asc"
            )
        else:
            invoices_domain = [
                ("state", "not in", ["draft", "cancel"]),
                ("name", "!=", False),
                ("journal_id", "in", self.journal_ids.ids),
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
            ]
            invoices = self.env["account.move"].search(
                invoices_domain, order="invoice_date asc, name asc, id asc"
            )

        self.invoice_ids = invoices

    def _compute_name(self):
        for rec in self:
            if rec.type == "sale":
                ledger_type = _("Sales")
            elif rec.type == "purchase":
                ledger_type = _("Purchases")

            name = _("%s VAT Ledger %s - %s") % (
                ledger_type,
                rec.date_from
                and fields.Date.from_string(rec.date_from).strftime("%d-%m-%Y")
                or "",
                rec.date_to
                and fields.Date.from_string(rec.date_to).strftime("%d-%m-%Y")
                or "",
            )
            if rec.reference:
                name = "%s - %s" % (name, rec.reference)
            rec.name = name

    def _compute_digital_files(self):
        self.ensure_one()
        return
        # TODO Internal methods
        # AFIP Wait "ISO-8859-1" and not utf-8
        # http://www.planillasutiles.com.ar/2015/08/como-descargar-los-archivos-de.html
