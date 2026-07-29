Certificado de retención en PDF a partir del pago, con numeración
secuencial propia, sobre las líneas de retención que
`l10n_ar_withholding` del core ya modela
(`account.move.l10n_ar_withholding_ids`). No implementa el cálculo de la
retención: solamente la emisión del comprobante.

Solo se certifican las retenciones que la compañía practicó como agente
de retención al pagarle a un proveedor. El campo del core mezcla esas
con las retenciones sufridas al cobrarle a un cliente, que se acreditan
con el certificado que emite el cliente.
