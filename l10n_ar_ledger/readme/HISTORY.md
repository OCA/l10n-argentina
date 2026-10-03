## 4.0.0.0.1 (2023-02-23)

- Se agrega el módulo base

## 18.0.1.0.0 (2026-07-29)

- Migración a 18.0: `document_number`/`l10n_ar_currency_rate` (campos de
  la era anterior a `l10n_latam_invoice_document`) reemplazados por
  `l10n_latam_document_number`/`invoice_currency_rate`; corrección de un
  compute sin `@api.depends`; corrección del acumulador del Crédito
  Fiscal Computable.
