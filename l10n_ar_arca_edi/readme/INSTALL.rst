This module depends on the following Odoo modules:

* ``l10n_ar`` -- Argentina Accounting Localization
* ``account_edi`` -- Electronic Data Interchange base

The following Python libraries are required:

* ``cryptography`` -- For RSA key generation, CSR creation, and CMS/PKCS#7
  signing.
* ``zeep`` -- SOAP client for communicating with ARCA web services (WSAA and
  WSFEv1).
* ``lxml`` -- XML processing for building and parsing SOAP requests/responses.

All three libraries are included in the official Odoo 19 Docker image. If you
are running Odoo outside Docker, install them with::

    pip install cryptography zeep lxml
