##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
try:
    from base64 import encodebytes
except ImportError:  # 3+
    from base64 import encodestring as encodebytes

import logging
import re
from ast import literal_eval

from odoo import _, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


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

    def format_amount(self, amount, padding=15, decimals=2, invoice=False):
        # Fet amounts on correct sign despite conifiguration on taxes and tax
        # codes
        if (
            invoice
            and invoice.l10n_latam_document_type_id.code
            in ["39", "40", "41", "66", "99"]
            and invoice.move_type in ["in_refund", "out_refund"]
        ):
            amount = -amount

        if amount < 0:
            template = "-{:0>%dd}" % (padding - 1)
        else:
            template = "{:0>%dd}" % (padding)
        return template.format(int(round(abs(amount) * 10**decimals, decimals)))

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
        for v, v in alicuotas.items():
            lines += v
        self.REGDIGITAL_CV_ALICUOTAS = "\r\n".join(lines)

        impo_alicuotas = {}
        if self.type == "purchase":
            impo_alicuotas = self.get_REGDIGITAL_CV_ALICUOTAS(impo=True)
            lines = []
            for v, v in impo_alicuotas.items():
                lines += v
            self.REGDIGITAL_CV_COMPRAS_IMPORTACIONES = "\r\n".join(lines)
        alicuotas.update(impo_alicuotas)
        self.get_REGDIGITAL_CV_CBTE()

    def get_point_of_sale(self, invoice):
        if self.type == "sale":
            return "{:0>5d}".format(invoice.journal_id.l10n_ar_afip_pos_number)
        else:
            return invoice.l10n_latam_document_number[:5]

    def get_partner_document_code(self, partner):
        if partner.l10n_ar_afip_responsibility_type_id.code == "5":
            res = str(
                partner.l10n_latam_identification_type_id.l10n_ar_afip_code
            ).zfill(2)
            return res
        return "80"

    def get_partner_document_number(self, partner):
        if partner.l10n_ar_afip_responsibility_type_id.code == "5":
            number = partner.vat or ""
            number = re.sub("[^0-9]", "", number)
        else:
            number = partner.vat
        if number is not False:
            return number.rjust(20, "0")
        else:
            raise ValidationError(
                _(
                    "Partner "
                    + partner.name
                    + " has not CUIT/CUIL or DNI. Required fro VAT Ledger Book."
                )
            )

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
            vat_taxes = inv._get_vat()
            lines = []

            for tax in vat_taxes:
                lines.append(
                    "".join(
                        self.get_tax_row(
                            inv,
                            tax["BaseImp"],
                            tax["Id"],
                            tax["Importe"],
                            impo=impo,
                        )
                    )
                )
            res[inv] = lines
        return res

    # REGDIGITAL_CV_CBTE Methods

    def get_vat_import(self, vat, code):
        import_vat = 0
        for v in vat:
            if v["Id"] == code:
                import_vat = import_vat + v["Importe"]
        return import_vat

    def _check_partners(self, invoices):
        if self.type == "purchase":
            partners = invoices.mapped("commercial_partner_id").filtered(
                lambda r: r.l10n_latam_identification_type_id.l10n_ar_afip_code
                in (False, 99)
                or not r.vat
            )
            if partners:
                raise ValidationError(
                    _(
                        "On purchase digital, partner document type is mandatory "
                        "and it must be different from 99. "
                        "Partners: \r\n\r\n"
                        "%s"
                    )
                    % "\r\n".join(
                        ["[%i] %s" % (p.id, p.display_name) for p in partners]
                    )
                )

    def _get_aliquots(self, inv):
        vat_taxes = []
        vat_exempt_base_amount = 0
        if inv.l10n_latam_document_type_id.code not in ["11", "12", "13"]:
            for invl in inv.invoice_line_ids:
                for tax in invl.tax_ids:
                    if tax.tax_group_id.l10n_ar_vat_afip_code not in ["1", "2"]:
                        if tax.id not in vat_taxes:
                            vat_taxes.append(tax.id)
                    if self.type == "purchase":
                        if tax.amount == 0:
                            vat_exempt_base_amount += invl.price_subtotal
        return len(vat_taxes)

    def get_REGDIGITAL_CV_CBTE(self):
        self.ensure_one()
        res = []
        invoices = self.get_digital_invoices().filtered(lambda r: r.state != "cancel")
        self._check_partners(invoices)

        for inv in invoices:
            qty_ali = self._get_aliquots(inv)
            currency_rate = inv.l10n_ar_currency_rate
            currency_code = inv.currency_id.l10n_ar_afip_code
            doc_number = int(inv.name.split("-")[2])
            amounts = inv._l10n_ar_get_amounts()

            row = [
                # Campo 1: Fecha de comprobante
                fields.Date.from_string(inv.invoice_date).strftime("%Y%m%d"),
                # Campo 2: Tipo de Comprobante.
                "{:0>3d}".format(int(inv.l10n_latam_document_type_id.code)),
                # Campo 3: Punto de Venta
                self.get_point_of_sale(inv),
                # Campo 4: Número de Comprobante
                "{:0>20d}".format(doc_number),
            ]

            if self.type == "sale":
                # Campo 5: Número de Comprobante Hasta.
                row.append("{:0>20d}".format(doc_number))
            else:
                # Campo 5: Despacho de importación
                if inv.l10n_latam_document_type_id.code == "66":
                    row.append(
                        (inv.l10n_latam_document_number or inv.number or "").rjust(
                            16, "0"
                        )
                    )
                else:
                    row.append("".rjust(16, " "))

            row += [
                # Campo 6: Código de documento del comprador.
                self.get_partner_document_code(inv.commercial_partner_id),
                # Campo 7: Número de Identificación del comprador
                self.get_partner_document_number(inv.commercial_partner_id),
                # Campo 8: Apellido y Nombre del comprador.
                inv.commercial_partner_id.name.ljust(30, " ")[:30],
                # Campo 9: Importe Total de la Operación.
                self.format_amount(inv.amount_total, invoice=inv),
            ]

            if self.type == "sale":
                row += [
                    # Campo 10: Importe total de conceptos que no integran el
                    # precio neto gravado
                    self.format_amount(amounts["vat_untaxed_base_amount"], invoice=inv),
                    # Campo 11: Percepción a no categorizados TODO
                    self.format_amount(0, invoice=inv),
                    # Campo 12: Importe de operaciones exentas
                    self.format_amount(amounts["vat_exempt_base_amount"], invoice=inv),
                    # Campo 13: Importe de percepciones o pagos a cuenta de
                    # impuestos nacionales TODO
                    self.format_amount(0, invoice=inv),
                    # Campo 14: Importe de percepciones de ingresos brutos
                    self.format_amount(amounts["iibb_perc_amount"], invoice=inv),
                ]
            else:
                row += [
                    # Campo 10: Importe total de conceptos que no integran el
                    # precio neto gravado
                    self.format_amount(amounts["vat_untaxed_base_amount"], invoice=inv),
                    # Campo 11: Importe de operaciones exentas
                    self.format_amount(amounts["vat_exempt_base_amount"], invoice=inv),
                    # Campo 12: Importe de percepciones o pagos a cuenta del
                    # Impuesto al Valor Agregado
                    self.format_amount(amounts["vat_perc_amount"], invoice=inv),
                    # Campo 13: Importe de percepciones o pagos a cuenta de
                    # impuestos nacionales TODO
                    self.format_amount(0, invoice=inv),
                    # Campo 14: Importe de percepciones de ingresos brutos
                    self.format_amount(amounts["iibb_perc_amount"], invoice=inv),
                ]

            row += [
                # Campo 15: Importe de percepciones de impuestos municipales
                self.format_amount(amounts["mun_perc_amount"], invoice=inv),
                # Campo 16: Importe de impuestos internos
                self.format_amount(amounts["intern_tax_amount"], invoice=inv),
                # Campo 17: Código de Moneda
                str(currency_code),
                # Campo 18: Tipo de Cambio
                self.format_amount(currency_rate, padding=10, decimals=6),
                # Campo 19: Cantidad de alícuotas de IVA
                str(qty_ali),
                # Campo 20: Código de operación.
                # WARNING. segun la plantilla es 0 si no es ninguna
                # TODO ver que no se informe un codigo si no correpsonde,
                # tal vez da error
                # TODO ADIVINAR E IMPLEMENTAR, VA A DAR ERROR
                # inv.fiscal_position_id.afip_code or '0',
                "0",
            ]

            if self.type == "sale":
                row += [
                    # Campo 21: Otros Tributos
                    self.format_amount(amounts["other_taxes_amount"], invoice=inv),
                    # Campo 22: Vencimiento comprobante
                    (
                        inv.l10n_latam_document_type_id.code
                        in [
                            "19",
                            "20",
                            "21",
                            "16",
                            "55",
                            "81",
                            "82",
                            "83",
                            "110",
                            "111",
                            "112",
                            "113",
                            "114",
                            "115",
                            "116",
                            "117",
                            "118",
                            "119",
                            "120",
                            "201",
                            "202",
                            "203",
                            "206",
                            "207",
                            "208",
                            "211",
                            "212",
                            "213",
                        ]
                        and "00000000"
                        or fields.Date.from_string(
                            inv.invoice_date_due or inv.invoice_date
                        ).strftime("%Y%m%d")
                    ),
                ]
            else:
                # Campo 21: Crédito Fiscal Computable
                if self.prorate_tax_credit:
                    if self.prorate_type == "global":
                        row.append(self.format_amount(0, invoice=inv))
                    else:
                        # row.append(self.format_amount(0))
                        # por ahora no implementado pero seria lo mismo que
                        # sacar si prorrateo y que el cliente entre en el digital
                        # en cada comprobante y complete cuando es en
                        # credito fiscal computable
                        raise ValidationError(
                            _(
                                "Para utilizar el prorrateo por comprobante:\n"
                                '1) Exporte los archivos sin la opción "Proratear '
                                'Crédito de Impuestos"\n2) Importe los mismos '
                                "en el aplicativo\n3) En el aplicativo de afip, "
                                "comprobante por comprobante, indique el valor "
                                'correspondiente en el campo "Crédito Fiscal '
                                'Computable"'
                            )
                        )
                else:
                    imp_neto = 0
                    imp_liquidado = 0
                    vats = inv._get_vat()
                    for v in vats:
                        if v["Id"] in ["3", "4", "5", "6", "8", "9"]:
                            imp_neto += v["BaseImp"]
                            imp_liquidado = v["BaseImp"] + v["Importe"]
                    row.append(self.format_amount(round(imp_liquidado, 2), invoice=inv))

                row += [
                    # Campo 22: Otros Tributos
                    self.format_amount(amounts["other_taxes_amount"], invoice=inv),
                    # TODO Implementar Campo 23, 24 y 25
                    # Campo 23: CUIT Emisor / Corredor
                    # Se informará sólo si en el campo "Tipo de Comprobante" se
                    # consigna '033', '058', '059', '060' ó '063'. Si para
                    # éstos comprobantes no interviene un tercero en la
                    # operación, se consignará la C.U.I.T. del informante. Para
                    # el resto de los comprobantes se completará con ceros
                    self.format_amount(0, padding=11, invoice=inv),
                    # Campo 24: Denominación Emisor / Corredor
                    "".ljust(30, " ")[:30],
                    # Campo 25: IVA Comisión
                    # Si el campo 23 es distinto de cero se consignará el
                    # importe del I.V.A. de la comisión
                    self.format_amount(0, invoice=inv),
                ]
            res.append("".join(row))
        self.REGDIGITAL_CV_CBTE = "\r\n".join(res)
