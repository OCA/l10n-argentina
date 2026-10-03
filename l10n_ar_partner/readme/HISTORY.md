## 4.0.0.0.1 (2023-02-23)

- Se agrega el módulo base

## 18.0.1.0.0 (2026-07-29)

- Migración a 18.0. `update_from_padron()` reescrito para usar
  `l10n_ar_arca_ws` (WSAA) y la biblioteca `arcalib`, en lugar de
  `l10n_ar_afipws` (pyafipws/pysimplesoap), no migrado a 18.0.

## 20.0.1.0.0

- Migración a 20.0. El tipo de identificación se lee de
  `l10n_ar_afip_code`, que el núcleo calcula a partir de los
  identificadores del contacto (`l10n_latam_base` ya no existe en Odoo 20).
- El tipo de persona del padrón ya no se escribe: en Odoo 20 el núcleo
  (`l10n_ar`) calcula "Es una empresa" a partir del prefijo del CUIT.
