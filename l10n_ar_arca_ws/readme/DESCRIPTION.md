Capa de transporte para los webservices de ARCA (Agencia de Recaudación
y Control Aduanero, ex AFIP): autenticación WSAA por certificado (Login
Ticket Request firmado en CMS/PKCS#7) y caché de token/sign por
compañía, ambiente y servicio.

Este módulo no implementa ningún webservice de negocio (factura
electrónica, constatación de comprobantes, etc): solamente el transporte
común que usan los demás módulos `l10n_ar_arca_*`. Los bindings de los
webservices y el armado del sobre SOAP provienen de la biblioteca
[arcalib](https://pypi.org/project/arcalib/) (PyPI, MIT), que genera los
tipos con `xsdata` a partir de los WSDL oficiales de ARCA, siguiendo el
mismo patrón de `nfelib` (Brasil) y `sifen` (Paraguay).

El certificado se gestiona con el modelo `certificate.certificate` del
propio core de Odoo: este módulo no define un modelo de certificado
propio.
