##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.l10n_ar.tests.common import TestAr


@tagged("post_install", "-at_install")
class TestAccountVatLedger(TestAr):
    """Regression tests for the digital files field formatting."""

    @classmethod
    def setUpClass(cls, chart_template_ref="l10n_ar.l10nar_ri_chart_template"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.ledger = cls.env["account.vat.ledger"].new(
            {"type": "purchase", "company_id": cls.company_ri.id}
        )

    def _partner(self, vat, responsibility_xmlid, identification_xmlid):
        return self.env["res.partner"].create(
            {
                "name": "Test partner",
                "vat": vat,
                "l10n_ar_afip_responsibility_type_id": self.env.ref(
                    responsibility_xmlid
                ).id,
                "l10n_latam_identification_type_id": self.env.ref(
                    identification_xmlid
                ).id,
            }
        )

    def test_document_number_strips_separators_for_any_responsibility(self):
        """The VAT is stored the way the user types it, with separators.

        The digital files use a fixed position layout: keeping the separators
        shifts every following field of the line and AFIP rejects the file.
        Before this fix only Consumidor Final was sanitized.
        """
        partner = self._partner("30-71429569-8", "l10n_ar.res_IVARI", "l10n_ar.it_cuit")
        self.assertEqual(
            self.ledger.get_partner_document_number(partner),
            "00000000030714295698",
        )
        self.assertEqual(len(self.ledger.get_partner_document_number(partner)), 20)

    def test_document_number_strips_separators_for_consumidor_final(self):
        """The behaviour that already worked must keep working."""
        partner = self._partner("20-22222222-3", "l10n_ar.res_CF", "l10n_ar.it_cuit")
        self.assertEqual(
            self.ledger.get_partner_document_number(partner),
            "00000000020222222223",
        )

    def test_document_number_without_vat_raises(self):
        """An empty VAT used to produce twenty zeros instead of an error."""
        partner = self._partner(False, "l10n_ar.res_IVARI", "l10n_ar.it_cuit")
        with self.assertRaises(ValidationError):
            self.ledger.get_partner_document_number(partner)

    def test_aliquots_count_matches_the_rate_records(self):
        """Field 19 of REGDIGITAL_CV_CBTE must match the number of records
        the same invoice produces in REGDIGITAL_CV_ALICUOTAS.

        Both come from different code paths: the count from `_get_aliquots`
        and the records from the core `_get_vat()`. A tax without VAT AFIP
        code (an IIBB perception) used to be counted here but never produced
        a rate record, so AFIP rejected the pair of files.
        """
        invoice = self.init_invoice(
            "out_invoice",
            partner=self.res_partner_adhoc,
            products=self.product_iva_21,
        )
        perception = self.env["account.tax"].create(
            {
                "name": "Perception IIBB (test)",
                "amount": 3.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": self.company_ri.id,
                "tax_group_id": self.tax_perc_iibb.tax_group_id.id,
            }
        )
        invoice.invoice_line_ids[0].tax_ids = [
            (4, self.tax_21.id),
            (4, perception.id),
        ]
        invoice.action_post()

        self.assertEqual(
            self.ledger._get_aliquots(invoice),
            len(invoice._get_vat()),
            "field 19 must match the number of REGDIGITAL_CV_ALICUOTAS records",
        )
        self.assertEqual(self.ledger._get_aliquots(invoice), 1)
