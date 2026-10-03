# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import TransactionCase


class TestL10nArBank(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.abn = cls.env.ref("l10n_ar_bank.00005")
        cls.amex = cls.env.ref("l10n_ar_bank.00295")
        cls.partner = cls.env["res.partner"].create({"name": "Cliente AR"})

    def _create_account(self, **vals):
        return self.env["res.partner.bank"].create(
            {
                "partner_id": self.partner.id,
                "account_number": "2850590940090418135201",
                **vals,
            }
        )

    def test_bank_list_loaded(self):
        self.assertEqual(self.abn._name, "l10n_ar_bank.bank")
        self.assertEqual(self.abn.code, "00005")
        self.assertEqual(self.abn.bic, "ABNAMRO")
        self.assertEqual(self.abn.state_id, self.env.ref("base.state_ar_c"))
        self.assertEqual(self.abn.country_id, self.env.ref("base.ar"))
        banks = self.env["l10n_ar_bank.bank"].search([])
        self.assertEqual(len(banks), 81)
        self.assertFalse([bank.id for bank in banks if not bank.code])

    def test_display_name_and_search_by_code(self):
        self.assertEqual(self.abn.display_name, "00005 - Abn  Amro Bank N. V.")
        found = self.env["l10n_ar_bank.bank"].name_search("00295")
        self.assertEqual([item[0] for item in found], [self.amex.id])

    def test_account_filled_from_bank(self):
        account = self._create_account(l10n_ar_bank_id=self.amex.id)
        self.assertEqual(account.bank_name, self.amex.name)
        self.assertEqual(account.bank_bic, "AEXP")
        self.assertEqual(account.street, "Arenales 707")
        self.assertEqual(account.zip, "C1061AAA")
        self.assertEqual(account.city, "Buenos Aires")
        self.assertEqual(account.state_id, self.env.ref("base.state_ar_c"))

    def test_switch_bank_replaces_all_data(self):
        account = self._create_account(l10n_ar_bank_id=self.amex.id)
        account.l10n_ar_bank_id = self.abn
        self.assertEqual(account.bank_name, self.abn.name)
        self.assertEqual(account.bank_bic, "ABNAMRO")
        self.assertEqual(account.street2, "piso pb")
        # ABN has no zip: the zip of the previous bank must not stay behind.
        self.assertFalse(account.zip)

    def test_without_bank_keeps_typed_data(self):
        account = self._create_account(bank_name="Banco a mano", bank_bic="MANUAL")
        self.assertFalse(account.l10n_ar_bank_id)
        self.assertEqual(account.bank_name, "Banco a mano")
        self.assertEqual(account.bank_bic, "MANUAL")
