##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class AccountVatLedgerXlsx(models.AbstractModel):
    _name = "report.l10n_ar_ledger.account_vat_ledger_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Report VAT Ledger XLSX"

    def generate_xlsx_report(self, workbook, data, vat_ledger):
        if vat_ledger.invoice_ids:
            report_name = "IVA Ventas"
            if vat_ledger.type == "purchase":
                report_name = "IVA Compras"

            sheet = workbook.add_worksheet(report_name[:31])
            h = "#"
            money_format = workbook.add_format(
                {"num_format": "$ 0" + h + h + "." + h + h + "," + h + h}
            )
            bold = workbook.add_format({"bold": True})
            sheet.write(1, 0, vat_ledger.display_name, bold)

            titles = [
                "Fecha",
                "Razón Social",
                "CUIT",
                "Responsabilidad AFIP",
                "Tipo de Comprobante",
                "Nro Comprobante",
                "Neto gravado",
                "Neto no gravado",
                "Neto exento",
                "IVA 27%",
                "IVA 21%",
                "IVA 10.5%",
                "Percepción de IVA",
                "Perc IIBB",
                "Percepciones Municipales",
                "Otras Percepciones",
                "Impuestos Internos",
                "Otros",
                "Total gravado",
                "Total",
            ]
            for i, title in enumerate(titles):
                sheet.write(3, i, title, bold)

            row = 4
            index = 0
            sheet.set_column("A:F", 30)

            for obj in vat_ledger.invoice_ids:
                sheet.write(
                    row + index, 0, obj.invoice_date.strftime("%Y-%m-%d")
                )  # Fecha
                sheet.write(row + index, 1, obj.partner_id.name)  # Razón Social
                if obj.partner_id.vat:  # CUIT
                    sheet.write(row + index, 2, obj.partner_id.vat)
                else:
                    sheet.write(row + index, 2, "-")
                sheet.write(
                    row + index,
                    3,
                    obj.partner_id.l10n_ar_afip_responsibility_type_id.name,
                )  # Responsabilidad AFIP
                sheet.write(
                    row + index, 4, obj.l10n_latam_document_type_id.name
                )  # Tipo de Comprobante
                sheet.write(row + index, 5, obj.name)  # Nro Comprobante

                amounts = obj._l10n_ar_get_amounts()
                credit = 1
                if obj.l10n_latam_document_type_id.internal_type == "credit_note":
                    credit = -1

                netoG = amounts["vat_taxable_amount"]
                sheet.write(
                    row + index, 6, netoG * credit, money_format
                )  # Neto gravado

                netoN = amounts["vat_untaxed_base_amount"]
                sheet.write(
                    row + index, 7, netoN * credit, money_format
                )  # Neto no gravado

                netoE = amounts["vat_exempt_base_amount"]
                sheet.write(row + index, 8, netoE * credit, money_format)  # Neto exento

                iva27 = vat_ledger.get_vat_import(obj._get_vat(), "6")
                sheet.write(row + index, 9, iva27 * credit, money_format)  # IVA 27%

                iva21 = vat_ledger.get_vat_import(obj._get_vat(), "5")
                sheet.write(row + index, 10, iva21 * credit, money_format)  # IVA 21%

                iva105 = vat_ledger.get_vat_import(obj._get_vat(), "4")
                sheet.write(row + index, 11, iva105 * credit, money_format)  # IVA 10.5%

                perc_iva = amounts["vat_perc_amount"]
                sheet.write(
                    row + index, 12, perc_iva * credit, money_format
                )  # Perpceción IVA

                perc_iibb = amounts["iibb_perc_amount"]
                sheet.write(
                    row + index, 13, perc_iibb * credit, money_format
                )  # Perpceción IIBB

                perc_mun = amounts["mun_perc_amount"]
                sheet.write(
                    row + index, 14, perc_mun * credit, money_format
                )  # Percepciones Municipales

                perc_other = amounts["other_perc_amount"]
                sheet.write(
                    row + index, 15, perc_other * credit, money_format
                )  # Otras Percepciones

                internal_taxes = amounts["intern_tax_amount"]
                sheet.write(
                    row + index, 16, internal_taxes * credit, money_format
                )  # Impuestos Internos

                other = amounts["other_taxes_amount"]
                sheet.write(row + index, 17, other * credit, money_format)  # Otros

                total_net = netoG + iva27 + iva21 + iva105 + other
                sheet.write(
                    row + index, 18, total_net * credit, money_format
                )  # Total Gravado

                sheet.write(row + index, 19, obj.amount_total, money_format)  # Total
                row = row + 1
