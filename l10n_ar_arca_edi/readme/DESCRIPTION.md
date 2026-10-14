Factura electrónica de ARCA (ex AFIP) para el mercado interno, vía
WSFEv1: solicitud del CAE al validar la factura de venta, registro del
CAE y su vencimiento, tratamiento del rechazo (la factura queda validada
sin CAE, el error se informa en el chatter y se puede reintentar con el
botón "Solicitar CAE"), array de tributos, comprobante asociado en notas
de crédito y débito, fechas de servicio y el código QR obligatorio (RG
4892/2020) en el PDF del comprobante.

Este módulo depende de `l10n_ar_arca_ws` (transporte WSAA) y reutiliza
por completo el cálculo de totales y alícuotas del core de Odoo
(`account.move._get_vat()`, `account.move._l10n_ar_get_amounts()`): aquí
no se reimplementa ninguna regla impositiva.

El ruteo hacia otros webservices de ARCA es un punto de extensión
(`_l10n_ar_arca_webservice`), de modo que agregar uno nuevo no obliga a
tocar este módulo.

Consulte el ROADMAP para lo que todavía **no** está implementado (cron
de reenvío de pendientes, `FECompConsultar`, cotización de moneda por la
propia ARCA) y para lo que fue escrito a partir de la lectura de la
especificación pero aún no está validado contra el ambiente de
homologación de ARCA.
