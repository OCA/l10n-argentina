Certificado de retención en PDF a partir del pago a proveedor, sobre las
líneas de retención que `l10n_ar_withholding` del core ya modela
(`account.payment.withholding_line_ids`). No implementa el cálculo de la
retención ni la numeración: el número de cada certificado es el que el
core asigna a la línea al confirmar el pago, desde la secuencia de
retención configurada en el impuesto.

Solo se certifican las retenciones que la compañía practicó como agente
de retención al pagarle a un proveedor (impuestos de compra), en pagos
confirmados. Las retenciones sufridas al cobrarle a un cliente se
acreditan con el certificado que emite el cliente.
