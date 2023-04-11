##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
try:
    from base64 import encodebytes
except ImportError:  # 3+
    from base64 import encodestring as encodebytes

from ast import literal_eval

from odoo import _, fields, models


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
        # AFIP Wait "ISO-8859-1" and not utf-8
        # http://www.planillasutiles.com.ar/2015/08/como-descargar-los-archivos-de.html
        if self.REGDIGITAL_CV_ALICUOTAS:
            self.digital_aliquots_filename = _("Alicuots_%s_%s.txt") % (
                self.type,
                self.date_to,
            )
            self.digital_aliquots_file = encodebytes(
                self.REGDIGITAL_CV_ALICUOTAS.encode("ISO-8859-1")
            )
        else:
            self.digital_aliquots_file = False
            self.digital_aliquots_filename = False
        if self.REGDIGITAL_CV_COMPRAS_IMPORTACIONES:
            self.digital_import_aliquots_filename = _("Import_Alicuots_%s_%s.txt") % (
                self.type,
                self.date_to,
            )
            self.digital_import_aliquots_file = encodebytes(
                self.REGDIGITAL_CV_COMPRAS_IMPORTACIONES.encode("ISO-8859-1")
            )
        else:
            self.digital_import_aliquots_file = False
            self.digital_import_aliquots_filename = False
        if self.REGDIGITAL_CV_CBTE:
            self.digital_vouchers_filename = _("Vouchers_%s_%s.txt") % (
                self.type,
                self.date_to,
            )
            self.digital_vouchers_file = encodebytes(
                self.REGDIGITAL_CV_CBTE.encode("ISO-8859-1")
            )
        else:
            self.digital_vouchers_file = False
            self.digital_vouchers_filename = False

    def compute_digital_data(self):
        alicuotas = self.get_REGDIGITAL_CV_ALICUOTAS()
        lines = []
        for v in alicuotas.items():
            lines += v
        self.REGDIGITAL_CV_ALICUOTAS = "\r\n".join(lines)

        impo_alicuotas = {}
        if self.type == "purchase":
            impo_alicuotas = self.get_REGDIGITAL_CV_ALICUOTAS(impo=True)
            lines = []
            for v in impo_alicuotas.items():
                lines += v
            self.REGDIGITAL_CV_COMPRAS_IMPORTACIONES = "\r\n".join(lines)
        alicuotas.update(impo_alicuotas)
        # TODO get_REGDIGITAL_CV_CBTE method
        # self.get_REGDIGITAL_CV_CBTE()

    def get_partner_document_code(self, partner):
        if partner.l10n_ar_afip_responsibility_type_id.code == "5":
            res = str(
                partner.l10n_latam_identification_type_id.l10n_ar_afip_code
            ).zfill(2)
            return res
        return "80"

    def get_digital_invoices(self, return_skiped=False):
        self.ensure_one()
        invoices = self.env["account.move"].search(
            [
                ("l10n_latam_document_type_id.export_to_digital", "=", True),
                ("id", "in", self.invoice_ids.ids),
            ],
            order="invoice_date asc",
        )
        if self.digital_skip_lines:
            skip_lines = literal_eval(self.digital_skip_lines)
            if isinstance(skip_lines, int):
                skip_lines = [skip_lines]
            to_skip = invoices.browse()
            for line in skip_lines:
                to_skip += invoices[line - 1]
            if return_skiped:
                return to_skip
            invoices -= to_skip
        return invoices

    def get_tax_row(self, invoice, base, code, tax_amount, impo=False):
        self.ensure_one()
        inv = invoice
        if self.type == "sale":
            doc_number = int(inv.name.split("-")[2])
            row = [
                # Campo 1: Tipo de Comprobante
                "{:0>3d}".format(int(inv.l10n_latam_document_type_id.code)),
                # Campo 2: Punto de Venta
                self.get_point_of_sale(inv),
                # Campo 3: Número de Comprobante
                "{:0>20d}".format(doc_number),
                # Campo 4: Importe Neto Gravado
                self.format_amount(base, invoice=inv),
                # Campo 5: Alícuota de IVA.
                str(code).rjust(4, "0"),
                # Campo 6: Impuesto Liquidado.
                self.format_amount(tax_amount, invoice=inv),
            ]
        elif impo:
            row = [
                # Campo 1: Despacho de importación.
                (inv.document_number or inv.number or "").rjust(16, "0"),
                # Campo 2: Importe Neto Gravado
                self.format_amount(base, invoice=inv),
                # Campo 3: Alícuota de IVA
                str(code).rjust(4, "0"),
                # Campo 4: Impuesto Liquidado.
                self.format_amount(tax_amount, invoice=inv),
            ]
        else:
            doc_number = int(inv.name.split("-")[2])
            row = [
                # Campo 1: Tipo de Comprobante
                str(inv.l10n_latam_document_type_id.code).zfill(3),
                # Campo 2: Punto de Venta
                "{:0>5d}".format(
                    int(
                        inv.l10n_latam_document_number[
                            : inv.l10n_latam_document_number.find("-")
                        ]
                    )
                ),
                # Campo 3: Número de Comprobante
                "{:0>20d}".format(doc_number),
                # Campo 4: Código de documento del vendedor
                self.get_partner_document_code(inv.commercial_partner_id),
                # Campo 5: Número de identificación del vendedor
                self.get_partner_document_number(inv.commercial_partner_id),
                # Campo 4: Importe Neto Gravado
                self.format_amount(base, invoice=inv),
                # Campo 5: Alícuota de IVA.
                str(code).rjust(4, "0"),
                # Campo 6: Impuesto Liquidado.
                self.format_amount(tax_amount, invoice=inv),
            ]
        return row

    def get_REGDIGITAL_CV_ALICUOTAS(self, impo=False):
        # Get Aliquots
        self.ensure_one()
        res = {}
        # Only vat taxes with codes 3, 4, 5, 6, 8, 9
        # http://contadoresenred.com/regimen-de-informacion-de-
        # compras-y-ventas-rg-3685-como-cargar-la-informacion/

        if impo:
            invoices = self.get_digital_invoices().filtered(
                lambda r: r.l10n_latam_document_type_id.code == "66"
                and r.state != "cancel"
            )
        else:
            invoices = self.get_digital_invoices().filtered(
                lambda r: r.l10n_latam_document_type_id.code
                not in ["66", "11", "12", "13"]
                and r.state != "cancel"
            )

        for inv in invoices:
            lines = []
            vat_taxes = self.env["account.move.line"]
            for mvl_tax in inv.l10n_latam_tax_ids:
                tax_group_id = mvl_tax.tax_group_id
                if (
                    tax_group_id.tax_type == "vat"
                    and tax_group_id.l10n_ar_vat_afip_code
                    in ["1", "2", "3", "4", "5", "6", "8", "9"]
                ):
                    vat_taxes += mvl_tax

            for mvl_tax in inv.line_ids:
                if (
                    mvl_tax.tax_ids
                    and mvl_tax.tax_ids[0].tax_group_id.l10n_ar_vat_afip_code == "3"
                ):
                    lines.append("".join(self.get_tax_row(inv, 0.0, 3, 0.0, impo=impo)))

            if not vat_taxes and inv.move_tax_ids.filtered(
                lambda r: r.tax_id.tax_group_id.tax_type == "vat"
                and r.tax_id.tax_group_id.l10n_ar_vat_afip_code
            ):
                lines.append("".join(self.get_tax_row(inv, 0.0, 3, 0.0, impo=impo)))

            for afip_code in vat_taxes.mapped("tax_group_id.l10n_ar_vat_afip_code"):
                taxes = vat_taxes.filtered(
                    lambda x: x.tax_group_id.l10n_ar_vat_afip_code == afip_code
                )
                imp_neto = sum(taxes.mapped("tax_base_amount"))
                imp_liquidado = sum(taxes.mapped("price_subtotal"))
                lines.append(
                    "".join(
                        self.get_tax_row(
                            inv,
                            imp_neto,
                            afip_code,
                            imp_liquidado,
                            impo=impo,
                        )
                    )
                )
            res[inv] = lines
        return res
