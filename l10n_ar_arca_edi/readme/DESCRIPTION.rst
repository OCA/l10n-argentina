This module integrates Odoo 19 Community Edition with ARCA (Agencia de
Recaudacion y Control Aduanero, formerly AFIP) web services for electronic
invoicing in Argentina.

It provides full support for the WSAA (authentication) and WSFEv1 (electronic
invoice authorization) web services, enabling automatic CAE (Codigo de
Autorizacion Electronico) generation when posting invoices.

Key features:

* **Certificate Management** -- Generate RSA private keys and CSR (Certificate
  Signing Request) directly from Odoo Settings.
* **WSAA Integration** -- Automatic authentication via CMS/PKCS#7 signed
  tickets with token caching until expiration.
* **WSFEv1 Integration** -- Electronic invoice authorization and CAE generation
  for all supported document types.
* **RG 5616 Compliant** -- Includes customer IVA condition reporting, mandatory
  since April 2025.
* **Dual Environment** -- Support for both testing (homologacion) and
  production environments.
* **Auto CAE on Post** -- Automatic CAE request when confirming invoices.
* **Certificate Expiration Monitoring** -- Automatic monitoring via scheduled
  cron job.

Supported document types:

+-------------------+---+---+---+------------+
| Type              | A | B | C | E (Export) |
+===================+===+===+===+============+
| Factura           | X | X | X | X          |
+-------------------+---+---+---+------------+
| Nota de Debito    | X | X | X | X          |
+-------------------+---+---+---+------------+
| Nota de Credito   | X | X | X | X          |
+-------------------+---+---+---+------------+
