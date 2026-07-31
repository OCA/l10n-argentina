- Cron de reproceso automático de las facturas validadas sin CAE (hoy el
  reenvío es manual, con el botón "Solicitar CAE"; la falla queda
  registrada en el chatter de la factura al validar, así que el usuario
  sabe que debe reintentar). Sin reconciliación por `FECompConsultar`:
  si ARCA ya aprobó y el `write()` local falla, la información de la
  aprobación se pierde y el reenvío manual puede quedar bloqueado.
- `FECompConsultar` (reconsulta de un comprobante ya autorizado) no
  implementado.
- Multimoneda: la cotización de moneda extranjera por la propia ARCA
  (`FEParamGetCotizacion`) no está implementada; se usa la cotización de
  Odoo (`invoice_currency_rate`, ya invertida al formato que ARCA
  espera).
- Array `Tributos`: se agrupa por `tax_group_id` de la factura. No fue
  verificado contra una muestra real de ARCA si la agrupación correcta
  es por grupo de impuesto o por línea (ver
  `_l10n_ar_arca_build_tributos` en `models/account_move.py`).
- Código QR (RG 4892/2020): implementado a partir de la lectura de la
  especificación pública, no verificado contra un QR real aprobado por
  ARCA en homologación.
- Constatación de comprobantes de proveedores por WSCDC antes de
  registrar la factura de compra: ver el módulo `l10n_ar_arca_verify`
  (etapa separada, sin integración automática con el flujo de compras).
- WSBFEv1 (bono fiscal electrónico) no implementado. El ruteo ya está
  preparado para él: alcanza con sobrescribir `_l10n_ar_arca_webservice`
  devolviendo la clave del webservice e implementar
  `_l10n_ar_arca_request_cae_<clave>`, sin tocar este módulo ni
  `l10n_ar_arca_edi_export`.
- WSMTXCA (factura electrónica con detalle por ítem) fuera de alcance:
  el WSFEv1 cubre el caso general y ninguna implementación libre de la
  localización argentina cubre hoy el WSMTXCA. Se incorporará si algún
  cliente lo necesita.
- `action_l10n_ar_arca_check_sequence` solamente diagnostica la
  divergencia de numeración (compara y avisa); no ajusta la secuencia
  por su cuenta, a propósito: ajustar la numeración contable fuera del
  flujo normal es una operación de riesgo.
