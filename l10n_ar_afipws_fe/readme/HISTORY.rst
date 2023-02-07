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
*
