* Add i18n support with Spanish translations for all UI elements and error
  messages.
* Implement WSFEX (Web Service de Factura Electronica de Exportacion) for
  export invoice authorization.
* Add PDF report with CAE barcode and QR code for printed invoices.
* Implement automatic retry logic for transient ARCA web service errors.
* Add support for associated invoices (``CbtesAsoc``) on credit and debit
  notes.
* Implement batch CAE request for multiple invoices (``FECAESolicitar`` with
  multiple ``FECAEDetRequest`` items).
* Add dashboard with CAE request statistics and error monitoring.
