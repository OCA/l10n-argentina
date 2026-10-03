## 4.0.0.0.1 (2023-02-23)

- Se agrega el módulo base

## 18.0.1.0.0 (2026-07-29)

- Migración a 18.0: `document_number`/`l10n_ar_currency_rate` (campos de
  la era anterior a `l10n_latam_invoice_document`) reemplazados por
  `l10n_latam_document_number`/`invoice_currency_rate`; corrección de un
  compute sin `@api.depends`; corrección del acumulador del Crédito
  Fiscal Computable.

## 20.0.1.0.0 (2026-10-03)

- Migración a 20.0: identificación del contacto tomada de
  `l10n_ar_afip_code` y `_get_id_number_sanitize()` del core (el modelo
  `l10n_latam.identification.type` ya no existe); archivos digitales
  escritos como `BinaryBytes`; permisos en `ir.access`; `report_file`
  quitado de las acciones de reporte.
