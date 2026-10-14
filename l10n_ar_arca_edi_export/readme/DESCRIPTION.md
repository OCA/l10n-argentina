Factura electrónica de exportación (letra E) por el WSFEXv1 de ARCA,
para diarios con sistema de punto de venta `FEERCEL`/`FEERCELP`. Depende
de `l10n_ar_arca_edi` y reutiliza los mismos campos de CAE: este módulo
solamente agrega el ruteo hacia el webservice de exportación cuando el
documento es letra E.

Agrega el CUIT País de ARCA en `res.country`, de carga manual, y el
campo `Permiso de embarque existente` para la exportación definitiva de
bienes.

El WSFEXv1 transporta ítems y total, sin campo para impuestos. Una
factura cuyo total no coincida con la suma de los ítems se rechaza antes
del envío, indicando qué quedó fuera, en lugar de dejar que ARCA la
rechace después de haber consumido el número de comprobante.
