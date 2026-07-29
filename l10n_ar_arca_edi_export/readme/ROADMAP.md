- `Tipo de exportación` (Tipo_expo) es de carga manual: el mapeo
  automático a partir de datos del core no fue verificado contra la
  especificación oficial de ARCA. A VERIFICAR antes de considerar
  automatizarlo.
- Cotización de moneda extranjera por ARCA (FEXGetPARAM_Cotizacion) no
  implementada: hoy se usa la cotización del propio Odoo (invertida al
  formato que ARCA espera, pesos por unidad extranjera).
- `CUIT País` (`res.country.l10n_ar_arca_cuit_pais`): no viene cargado
  para ningún país. Es una tabla propia de ARCA (código por país,
  distinto de `l10n_ar_afip_code`) que no fue obtenida de una fuente
  oficial. Debe configurarse manualmente por país antes de facturar una
  exportación hacia ese destino (el código levanta un error claro si
  falta, en lugar de enviar un valor equivocado). Cargarlo a partir de
  la tabla oficial de ARCA es un punto pendiente.
- `Items`: obligatorio e implementado a partir de las líneas de la
  factura, pero sin verificación contra una muestra real aprobada por
  ARCA (el mapeo de la bonificación y del código de unidad de medida
  quedan A VERIFICAR en homologación).
- `Permisos` (detalle de los permisos de embarque) no implementado. El
  campo `Permiso_existente` se envía como `N` en la exportación
  definitiva de bienes (Tipo_expo = 1) y no se envía en los demás tipos.
  Marcarlo como `S` se rechaza con un error claro mientras el array
  `Permisos` no exista, porque ARCA rechazaría el comprobante por falta
  del detalle.
- Una factura de exportación cuyo total no sea igual a la suma de los
  ítems (impuesto, percepción, redondeo de caja, descuento por pago
  anticipado embebido) se rechaza antes del envío: el WSFEXv1 solo
  transporta ítems y total, sin campo para impuestos. Soportar esos
  casos exige decidir cómo representarlos en el comprobante y no fue
  hecho.
- `Cmps_asoc` (comprobante asociado, para notas de crédito y débito de
  exportación) no implementado.
- WSBFEv1 (bono fiscal) fuera del alcance de este módulo.
