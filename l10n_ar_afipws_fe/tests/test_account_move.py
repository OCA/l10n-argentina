# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.l10n_ar.tests.common import TestArCommon


@tagged("post_install", "-at_install")
class TestAccountMoveAfipAmounts(TestArCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.res_partner_adhoc
        cls.journal = cls._create_journal(
            "preprinted",
            {
                "l10n_ar_afip_pos_number": 3,
                "l10n_ar_afip_pos_system": "RAW_MAW",
            },
        )

    def _build_wsfe_header(self, invoice):
        journal_model = self.env.registry["account.journal"]
        with patch.object(
            journal_model,
            "get_pyafipws_last_invoice",
            autospec=True,
            return_value=0,
        ):
            return invoice._build_afip_wsfe_header()

    def _create_wsfe_invoice(self, lines, move_type="out_invoice"):
        return self._create_invoice_ar(
            company_id=self.company_ri,
            journal_id=self.journal,
            move_type=move_type,
            partner_id=self.partner,
            invoice_line_ids=lines,
        )

    def _assert_header_amounts(self, header, **expected):
        amount_fields = {
            "imp_total",
            "imp_tot_conc",
            "imp_neto",
            "imp_op_ex",
            "imp_trib",
            "imp_iva",
        }
        self.assertEqual({key: header[key] for key in amount_fields}, expected)
        component_total = sum(
            float(header[key])
            for key in (
                "imp_tot_conc",
                "imp_neto",
                "imp_op_ex",
                "imp_trib",
                "imp_iva",
            )
        )
        self.assertAlmostEqual(float(header["imp_total"]), component_total, places=2)

    def test_wsfe_header_with_21_percent_vat(self):
        invoice = self._create_wsfe_invoice(
            [
                self._prepare_invoice_line(
                    product_id=self.product_iva_21,
                    price_unit=4_000_000,
                    tax_ids=self.tax_21,
                )
            ]
        )

        header = self._build_wsfe_header(invoice)

        self._assert_header_amounts(
            header,
            imp_total="4840000.00",
            imp_tot_conc="0.00",
            imp_neto="4000000.00",
            imp_op_ex="0.00",
            imp_trib="0.00",
            imp_iva="840000.00",
        )

    def test_wsfe_header_with_mixed_vat_categories(self):
        invoice = self._create_wsfe_invoice(
            [
                self._prepare_invoice_line(
                    product_id=self.product_iva_21,
                    price_unit=100,
                    tax_ids=self.tax_21,
                ),
                self._prepare_invoice_line(
                    product_id=self.product_no_gravado,
                    price_unit=50,
                    tax_ids=self.tax_no_gravado,
                ),
                self._prepare_invoice_line(
                    product_id=self.product_iva_exento,
                    price_unit=80,
                    tax_ids=self.tax_iva_exento,
                ),
            ]
        )

        header = self._build_wsfe_header(invoice)

        self._assert_header_amounts(
            header,
            imp_total="251.00",
            imp_tot_conc="50.00",
            imp_neto="100.00",
            imp_op_ex="80.00",
            imp_trib="0.00",
            imp_iva="21.00",
        )

    def test_wsfe_credit_note_header_uses_positive_amounts(self):
        credit_note = self._create_wsfe_invoice(
            [
                self._prepare_invoice_line(
                    product_id=self.product_iva_21,
                    price_unit=100,
                    tax_ids=self.tax_21,
                )
            ],
            move_type="out_refund",
        )

        header = self._build_wsfe_header(credit_note)

        self._assert_header_amounts(
            header,
            imp_total="121.00",
            imp_tot_conc="0.00",
            imp_neto="100.00",
            imp_op_ex="0.00",
            imp_trib="0.00",
            imp_iva="21.00",
        )
