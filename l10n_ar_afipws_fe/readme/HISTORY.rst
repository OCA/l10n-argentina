14.0.1.0.0 (2023-01-29)
~~~~~~~~~~~~~~~~~~~~~~~

* Refactorizacion completa del modulo y de sus metodos
* Se elimina necesidad de utilizar secuencias individuales para la numeracion de comprobantes, se usa las de odoo nativo
* Numeracion a prueba de fallos, integrado reproceso para recuperar CAE en caso de falta de conecciones
* Decoracion visual de numero de comprobante, para en la ux ofrecer informacion al usuario sobre el estado de AFIP del comprobantes
* Se mejoraron las vistas y su usabilidad
* Ahora es posible en caso de desincronizacion o probelmas con un comprobante, forzar su numero de cbte para recuperar los datos de AFIP.
* Se eliminaron metodos sin usar y codigo legacy
* Se crearon nuevos metodos builders y archivos por webservice, para mejor mantenimiento del codigo

14.0.1.0.1 (2023-02-23)
~~~~~~~~~~~~~~~~~~~~~~~
- Solo se permite forzar el número de comprobante en facturas de venta, si el usuario está en modo debug y si hay una desincronización de secuencias. Esto es útil para reparar errores de secuencias directamente desde la UI.
- Se agrega pyafipws al manifest y requirements para que la instalación de la librería sea automática.
- Se eliminan raise error en los mensajes de error XML. De esta forma, el mensaje de error se guarda en afip_message. El usuario puede entrar al registro y consultar el error. Esto es útil cuando se autorizan múltiples facturas.
- FIX: Solo se muestran los decoradores de errores de secuencia en facturas de venta
- FIX: Solo se muestra la pestaña AFIP si el comprobante es de venta. TODO: Luego al implementar la validación automática de comprobantes de venta contra AFIP se volverá a mostrar la tab.
- No se muestra mas la tab de "EDI" ya que esta localización no usa la funcionalidad EDI de odoo.

16.0.1.0.0 (2024-02-12)
~~~~~~~~~~~~~~~~~~~~~~~
- Nueva version del modulo, con mejoras y actualizaciones para la version 16.0
