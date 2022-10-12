# Base Module for AFIP Web Services

## Homologation / Production:

First it search for a paramter "afip.ws.env.type" if exists set the value:

* is production --> production
* is homologation --> homologation

Else

Search for 'server_mode' parameter on conf file. If that parameter:

* Has a value then we use "homologation",
* If no parameter, then "production"

## Includes:

* Wizard for install keys for Web Services.
* API for make request on the Web Services from Odoo.

The l10n_ar_afipws module allows Odoo ERP to access AFIP services at through Web Services. This module is a service for administrators and programmers, where they could configure the server, authentication and they will also have access to a generic API in Python to use the AFIP services.

Keep in mind that these keys are personal and may cause conflict publish them in the public repositories. 

## Contributors

* AdHoc SA
* Moldeo Interactive
* Exemax
* Codize

## Maintainer

This module is maintained by the Exemax-Codize team. Original develop by AdHoc SA
