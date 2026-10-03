## 20.0.1.0.0

Odoo 20 removed the `res.bank` model and moved `res.partner.bank` to `base`,
with the bank name, BIC and address as plain fields of the account. The bank
list moves to the `l10n_ar_bank.bank` model, linked to the bank account by the
`l10n_ar_bank_id` field, which fills those fields. The xmlids of the bank list
are kept (`l10n_ar_bank.<BCRA code>`).
