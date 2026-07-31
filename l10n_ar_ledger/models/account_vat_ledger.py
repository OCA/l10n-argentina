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

from odoo import _, api, fields, models
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
        compute="_compute_digital_files", readonly=True
    )
    digital_aliquots_filename = fields.Char(
        readonly=True,
        compute="_compute_digital_files",
    )
    digital_import_aliquots_file = fields.Binary(
        compute="_compute_digital_files", readonly=True
    )
    digital_import_aliquots_filename = fields.Char(
        readonly=True,
        compute="_compute_digital_files",
    )
    prorate_tax_credit = fields.Boolean()

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    type = fields.Selection([("sale", "Sale"), ("purchase", "Purchase")], required=True)
    date_from = fields.Date(
        required=True,
        readonly=True,
    )
    date_to = fields.Date(
        required=True,
        readonly=True,
    )
    journal_ids = fields.Many2many(
        "account.journal",
        "account_vat_ledger_journal_rel",
        "vat_ledger_id",
        "journal_id",
        string="Journals",
        required=True,
        readonly=True,
    )
    presented_ledger = fields.Binary(
        readonly=True,
    )
    presented_ledger_name = fields.Char()
    state = fields.Selection(
        [("draft", "Draft"), ("presented", "Presented"), ("cancel", "Cancelled")],
        required=True,
        default="draft",
    )
    note = fields.Html()

    name = fields.Char(compute="_compute_name")
    reference = fields.Char()
    invoice_ids = fields.Many2many(
        "account.move", string="Invoices", compute="_compute_data"
    )

    @api.depends("type", "journal_ids", "date_from", "date_to")
    def _compute_data(self):
        for rec in self:
            # `l10n_latam_document_number` is not a stored field (a compute
            # without store=True in the core): it cannot be used in a domain nor
            # in the `order` of a `search()`. `name` is the real sequence field
            # (stored) and, with `l10n_latam_use_documents=True` on the journal,
            # it is built from the same document number, which makes it the
            # right field to filter and order by, for both sales and
            # purchases.
            domain = [
                ("state", "not in", ["draft", "cancel"]),
                ("name", "!=", False),
                ("journal_id", "in", rec.journal_ids.ids),
                ("date", ">=", rec.date_from),
                ("date", "<=", rec.date_to),
            ]
            order = "invoice_date asc, name asc, id asc"
            rec.invoice_ids = self.env["account.move"].search(domain, order=order)

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

        # Layout de posicao fixa: `padding` e o tamanho TOTAL do campo, entao
        # o sinal negativo ocupa uma das posicoes (o numero fica com um
        # digito a menos). Equivalente exato ao template original
        # ("-{:0>%dd}" % (padding - 1) / "{:0>%dd}" % padding), so reescrito
        # sem percent-format para o ruff (UP031).
        sign = "-" if amount < 0 else ""
        digits = padding - 1 if amount < 0 else padding
        value = int(round(abs(amount) * 10**decimals, decimals))
        return f"{sign}{value:0>{digits}d}"

    def _compute_name(self):
        for rec in self:
            if rec.type == "sale":
                ledger_type = _("Sales")
            elif rec.type == "purchase":
                ledger_type = _("Purchases")

            name = _("%(ledger_type)s VAT Ledger %(date_from)s - %(date_to)s") % {
                "ledger_type": ledger_type,
                "date_from": rec.date_from
                and fields.Date.from_string(rec.date_from).strftime("%d-%m-%Y")
                or "",
                "date_to": rec.date_to
                and fields.Date.from_string(rec.date_to).strftime("%d-%m-%Y")
                or "",
            }
            if rec.reference:
                name = f"{name} - {rec.reference}"
            rec.name = name

    def action_present(self):
        self.write({"state": "presented"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_to_draft(self):
        self.write({"state": "draft"})

    def _compute_digital_files(self):
        self.ensure_one()
        # AFIP Wait "ISO-8859-1" and not utf-8
        # http://www.planillasutiles.com.ar/2015/08/como-descargar-los-archivos-de.html
        if self.REGDIGITAL_CV_ALICUOTAS:
            self.digital_aliquots_filename = _(
                "Alicuots_%(ledger_type)s_%(date_to)s.txt"
            ) % {"ledger_type": self.type, "date_to": self.date_to}
            self.digital_aliquots_file = encodebytes(
                self.REGDIGITAL_CV_ALICUOTAS.encode("ISO-8859-1")
            )
        else:
            self.digital_aliquots_file = False
            self.digital_aliquots_filename = False
        if self.REGDIGITAL_CV_COMPRAS_IMPORTACIONES:
            self.digital_import_aliquots_filename = _(
                "Import_Alicuots_%(ledger_type)s_%(date_to)s.txt"
            ) % {"ledger_type": self.type, "date_to": self.date_to}
            self.digital_import_aliquots_file = encodebytes(
                self.REGDIGITAL_CV_COMPRAS_IMPORTACIONES.encode("ISO-8859-1")
            )
        else:
            self.digital_import_aliquots_file = False
            self.digital_import_aliquots_filename = False
        if self.REGDIGITAL_CV_CBTE:
            self.digital_vouchers_filename = _(
                "Vouchers_%(ledger_type)s_%(date_to)s.txt"
            ) % {"ledger_type": self.type, "date_to": self.date_to}
            self.digital_vouchers_file = encodebytes(
                self.REGDIGITAL_CV_CBTE.encode("ISO-8859-1")
            )
        else:
            self.digital_vouchers_file = False
            self.digital_vouchers_filename = False

    def compute_digital_data(self):
        alicuotas = self.get_REGDIGITAL_CV_ALICUOTAS()
        lines = []
        for inv_lines in alicuotas.values():
            lines += inv_lines
        self.REGDIGITAL_CV_ALICUOTAS = "\r\n".join(lines)

        impo_alicuotas = {}
        if self.type == "purchase":
            impo_alicuotas = self.get_REGDIGITAL_CV_ALICUOTAS(impo=True)
            lines = []
            for inv_lines in impo_alicuotas.values():
                lines += inv_lines
            self.REGDIGITAL_CV_COMPRAS_IMPORTACIONES = "\r\n".join(lines)
        alicuotas.update(impo_alicuotas)
        self.get_REGDIGITAL_CV_CBTE()

    def get_point_of_sale(self, invoice):
        if self.type == "sale":
            return f"{invoice.journal_id.l10n_ar_afip_pos_number:0>5d}"
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
        """Number of the partner's identification, digits only, right aligned
        in 20 positions.

        The digital files use a fixed position layout, so any separator kept
        in the number (``30-71429569-8``) shifts every following field of the
        line and makes AFIP reject the whole file. The number is therefore
        sanitized for every responsibility type, not only for Consumidor
        Final, which is how the partner's VAT is usually stored.
        """
        number = re.sub("[^0-9]", "", partner.vat or "")
        if not number:
            raise ValidationError(
                _("Partner %s has no CUIT/CUIL or DNI. Required for VAT Ledger Book.")
                % partner.display_name
            )
        return number.rjust(20, "0")

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
            doc_number = inv._l10n_ar_get_document_number_parts(
                inv.l10n_latam_document_number, inv.l10n_latam_document_type_id.code
            )["invoice_number"]
            row = [
                # Campo 1: Tipo de Comprobante
                f"{int(inv.l10n_latam_document_type_id.code):0>3d}",
                # Campo 2: Punto de Venta
                self.get_point_of_sale(inv),
                # Campo 3: Número de Comprobante
                f"{doc_number:0>20d}",
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
                (inv.l10n_latam_document_number or "").rjust(16, "0"),
                # Campo 2: Importe Neto Gravado
                self.format_amount(base, invoice=inv),
                # Campo 3: Alícuota de IVA
                str(code).rjust(4, "0"),
                # Campo 4: Impuesto Liquidado.
                self.format_amount(tax_amount, invoice=inv),
            ]
        else:
            doc_number_parts = inv._l10n_ar_get_document_number_parts(
                inv.l10n_latam_document_number, inv.l10n_latam_document_type_id.code
            )
            row = [
                # Campo 1: Tipo de Comprobante
                str(inv.l10n_latam_document_type_id.code).zfill(3),
                # Campo 2: Punto de Venta
                "{:0>5d}".format(doc_number_parts["point_of_sale"]),
                # Campo 3: Número de Comprobante
                "{:0>20d}".format(doc_number_parts["invoice_number"]),
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
                lambda r: (
                    r.l10n_latam_document_type_id.code == "66" and r.state != "cancel"
                )
            )
        else:
            invoices = self.get_digital_invoices().filtered(
                lambda r: (
                    r.l10n_latam_document_type_id.code not in ["66", "11", "12", "13"]
                    and r.state != "cancel"
                )
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
                lambda r: (
                    r.l10n_latam_identification_type_id.l10n_ar_afip_code
                    in (False, "99")
                    or not r.vat
                )
            )
            if partners:
                raise ValidationError(
                    _(
                        "On purchase digital, partner document type is mandatory "
                        "and it must be different from 99. "
                        "Partners: \r\n\r\n"
                        "%s"
                    )
                    % "\r\n".join(f"[{p.id}] {p.display_name}" for p in partners)
                )

    def _get_aliquots(self, inv):
        """Number of VAT rates of the voucher, for field 19 of
        ``REGDIGITAL_CV_CBTE``.

        Must match the number of records the voucher generates in
        ``REGDIGITAL_CV_ALICUOTAS``, which comes from ``_get_vat()``: AFIP
        rejects the pair of files when the declared count differs from the
        rate records. ``_get_vat()`` keeps only tax groups whose
        ``l10n_ar_vat_afip_code`` is set and is not ``0``, ``1`` or ``2``, so
        the same filter is applied here. Taxes with no VAT code at all (an
        IIBB perception, for instance) were previously counted and made the
        count diverge.
        """
        vat_taxes = []
        if inv.l10n_latam_document_type_id.code not in ["11", "12", "13"]:
            for invl in inv.invoice_line_ids:
                for tax in invl.tax_ids:
                    vat_afip_code = tax.tax_group_id.l10n_ar_vat_afip_code
                    if vat_afip_code and vat_afip_code not in ["0", "1", "2"]:
                        if tax.id not in vat_taxes:
                            vat_taxes.append(tax.id)
        return len(vat_taxes)

    def get_REGDIGITAL_CV_CBTE(self):
        self.ensure_one()
        res = []
        invoices = self.get_digital_invoices().filtered(lambda r: r.state != "cancel")
        self._check_partners(invoices)

        for inv in invoices:
            qty_ali = self._get_aliquots(inv)
            # Tipo de Cambio: 1 when the document currency is the company
            # currency; otherwise pesos per foreign unit (the same convention
            # used in the WSFEv1 payload,
            # l10n_ar_arca_edi._l10n_ar_arca_currency_rate).
            currency_rate = (
                1.0
                if inv.currency_id == inv.company_id.currency_id
                else 1 / (inv.invoice_currency_rate or 1.0)
            )
            currency_code = inv.currency_id.l10n_ar_afip_code
            doc_number = inv._l10n_ar_get_document_number_parts(
                inv.l10n_latam_document_number, inv.l10n_latam_document_type_id.code
            )["invoice_number"]
            base_lines, _tax_lines = inv._get_rounded_base_and_tax_lines()
            amounts = inv._l10n_ar_get_amounts(base_lines)

            row = [
                # Campo 1: Fecha de comprobante
                fields.Date.from_string(inv.invoice_date).strftime("%Y%m%d"),
                # Campo 2: Tipo de Comprobante.
                f"{int(inv.l10n_latam_document_type_id.code):0>3d}",
                # Campo 3: Punto de Venta
                self.get_point_of_sale(inv),
                # Campo 4: Número de Comprobante
                f"{doc_number:0>20d}",
            ]

            if self.type == "sale":
                # Campo 5: Número de Comprobante Hasta.
                row.append(f"{doc_number:0>20d}")
            else:
                # Campo 5: Despacho de importación
                if inv.l10n_latam_document_type_id.code == "66":
                    row.append((inv.l10n_latam_document_number or "").rjust(16, "0"))
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
                    # Prorating per document is not implemented: the only
                    # field the module had to pick the mode ("prorate_type")
                    # was never declared, so this branch raised AttributeError
                    # every time it was reached. Until there is a real
                    # implementation, the manual guidance below is the only
                    # path.
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
                    imp_liquidado = 0
                    vats = inv._get_vat()
                    for v in vats:
                        if v["Id"] in ["3", "4", "5", "6", "8", "9"]:
                            imp_liquidado += v["BaseImp"] + v["Importe"]
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
