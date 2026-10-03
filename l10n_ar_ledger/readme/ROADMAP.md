- El Campo 11 (Percepción a no categorizados) y el Campo 13
  (Percepciones/pagos a cuenta de impuestos nacionales) del diseño
  `REGDIGITAL_CV_CBTE` (compras) salen siempre en cero (`TODO` heredado
  de la migración original de 14.0, no implementado).
- Los Campos 23, 24 y 25 (CUIT/Denominación/IVA del Corredor, aplicables
  solo a comprobantes de tipo 033/058/059/060/063) no están
  implementados: salen siempre en cero o vacíos.
- Prorrateo de Crédito Fiscal "global" (`prorate_tax_credit` marcado):
  no implementado. El único camino soportado es prorratear por
  comprobante fuera de Odoo (el propio error indica cómo).
- No hay ningún test de regresión con un archivo TXT esperado
  versionado: los tests de este módulo confirman que el TXT se genera
  sin levantar excepción y verifican algunos campos, no el archivo
  completo byte a byte. Compararlo contra un archivo esperado, generado
  a partir de un período real y revisado por el contador, es el próximo
  paso natural de esta suite.
- Ninguno de los 5 diseños de registro fue validado contra el validador
  oficial de ARCA ni contra homologación real.
