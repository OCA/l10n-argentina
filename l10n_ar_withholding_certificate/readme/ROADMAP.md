- Libro de retenciones sufridas (reporte consolidado por período)
  todavía no está implementado en esta versión: solo el certificado por
  pago.
- Numeración por secuencia global (`company_id` vacío en la
  `ir.sequence` de este módulo): compañías distintas en la misma base
  comparten la misma numeración de certificado. Si un agente de
  retención necesita una serie propia, registre otra `ir.sequence` con
  el mismo `code` (`l10n_ar_withholding_certificate`) y el `company_id`
  cargado: el `next_by_code` de Odoo ya prioriza la secuencia de la
  compañía cuando existe, sin necesidad de modificar código.
