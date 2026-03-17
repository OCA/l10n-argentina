# l10n_ar_arca_edi

[![pre-commit](https://img.shields.io/badge/pre--commit-passing-brightgreen)](https://github.com/leonobitech/l10n_ar_arca_edi)
[![tests](https://img.shields.io/badge/tests-passing-brightgreen)](https://github.com/leonobitech/l10n_ar_arca_edi)
[![License: AGPL-3](https://img.shields.io/badge/license-AGPL--3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Odoo](https://img.shields.io/badge/Odoo-19.0-blueviolet)](https://www.odoo.com)

**Odoo 19 Community** - Argentina ARCA Electronic Invoicing (WSAA / WSFEv1)

## Overview

This addon integrates Odoo Community Edition with ARCA (Agencia de Recaudación y Control Aduanero, formerly AFIP) web services for electronic invoicing in Argentina.

## Features

- **Certificate Management**: Generate RSA private keys and CSR (Certificate Signing Request) directly from Odoo Settings
- **WSAA Integration**: Automatic authentication with ARCA via CMS (PKCS#7) signed tickets
- **WSFEv1 Integration**: Electronic invoice authorization and CAE (Código de Autorización Electrónico) generation
- **RG 5616 Compliant**: Includes customer IVA condition reporting (mandatory since April 2025)
- **Dual Environment**: Support for both testing (homologación) and production environments
- **Auto CAE on Post**: Automatic CAE request when posting invoices
- **Token Caching**: WSAA tokens are cached and reused until expiration
- **Certificate Expiration**: Automatic monitoring via cron job

## Supported Documents

| Type | A | B | C | E (Export) |
|------|---|---|---|------------|
| Factura | ✅ | ✅ | ✅ | ✅ |
| Nota de Débito | ✅ | ✅ | ✅ | ✅ |
| Nota de Crédito | ✅ | ✅ | ✅ | ✅ |

## Requirements

### Odoo Modules
- `l10n_ar` (Argentina Accounting Localization)
- `account_edi` (Electronic Data Interchange base)

### Python Libraries
All included in the official Odoo 19 Docker image:
- `cryptography`
- `zeep`
- `lxml`

## Installation

1. Copy the `l10n_ar_arca_edi` folder to your Odoo addons path
2. Update the addons list: **Settings > Apps > Update Apps List**
3. Search and install **"Argentina - ARCA Electronic Invoicing"**

## Setup Guide

Everything is configured from **Settings > Invoicing > ARCA Electronic Invoicing** (top of the page).

### Step 1: Create Certificate (in Odoo)

1. Go to **Settings > Invoicing**
2. In the **ARCA Electronic Invoicing** section, click **"Create Certificate"**
3. Fill in the name (e.g., `MyCompany-Testing`), select company and environment
4. Click **"Create Certificate"**
5. Click **"Generate Key & CSR"** — this generates your private key and CSR

### Step 2: Create DN in ARCA Portal

Go to the ARCA portal to register your certificate:

**Testing (Homologación):**

1. Login at [https://auth.afip.gob.ar](https://auth.afip.gob.ar) with your CUIT and clave fiscal
2. In the search bar, type **"WSASS"**
3. Select **"WSASS - Autogestión Certificados Homologación"**
4. This takes you to: https://wsass-homo.afip.gob.ar/wsass/portal/main.aspx

**Production:**

1. Login at [https://auth.afip.gob.ar](https://auth.afip.gob.ar) with your CUIT and clave fiscal
2. Search for **"Administración de Certificados Digitales"**

> **Note**: If it's your first time, you may need to enable the WSASS service from **"Administrador de Relaciones"** first.

Once inside the WSASS portal:

1. In the left sidebar, click **"Nuevo Certificado"**
2. You'll see the form **"Crear DN y certificado"** with 3 fields:
   - **Nombre simbólico del DN**: Enter a name (e.g., `MyCompanyTesting`)
   - **CUIT del contribuyente**: Pre-filled with your CUIT
   - **Solicitud de certificado en formato PKCS#10**: Go back to Odoo, copy the CSR content using the copy button, and paste it here
3. Click **"Crear DN y obtener certificado"**
4. In the **Resultado** section below, the signed certificate will appear. It starts with `-----BEGIN CERTIFICATE-----` and ends with `-----END CERTIFICATE-----`. Copy the **entire** content (including those lines) and save it as a `.crt` file (e.g., `MyCompany-Testing.crt`)

### Step 3: Authorize wsfe Service in ARCA

Still in the WSASS portal:

1. In the left sidebar, click **"Crear autorización a servicio"**
2. You'll see the form **"Crear autorización"** with 5 fields:
   - **Nombre simbólico del DN a autorizar**: Select the DN you created in Step 2
   - **CUIT del DN a autorizar**: Pre-filled with your CUIT
   - **CUIT representado**: Enter your CUIT
   - **CUIT de quien genera la autorización**: Pre-filled with your CUIT
   - **Servicio al que desea acceder**: Select **"wsfe - Facturación Electrónica"**
3. Click **"Crear autorización de acceso"**

> **Important**: Without this step, the Test Connection will fail with "Computador no autorizado a acceder al servicio".

### Step 4: Upload Certificate (in Odoo)

1. Back in Odoo Settings, click **"Upload Certificate"**
2. Upload the `.crt` file you saved from ARCA
3. Click **"Upload"**

### Step 5: Test Connection

1. Click **"Test Connection"**
2. You should see a green toast: "Connection Successful. WSAA authentication successful. Token valid until YYYY-MM-DD HH:MM."
3. The token is typically valid for **12 hours** (assigned by ARCA, may vary in production). It is cached and renewed automatically when expired — no manual action required.

That's it! Your Odoo is now connected to ARCA.

### Step 6: Configure Journal

1. Go to **Invoicing > Configuration > Journals** (in Odoo Community, the app is called "Invoicing", not "Accounting")
2. Click on your sales journal (e.g., "Ventas Preimpreso")
3. Make sure **Use Documents** and **Is ARCA POS?** are checked
4. Set **ARCA POS System** to **"Online Invoice"** (this is the `RLI_RLM` mode required for electronic invoicing)
5. The **ARCA Electronic Invoicing** checkbox will be automatically enabled
6. Set your **ARCA POS Number** (the point of sale number registered in ARCA)

## Usage

Once configured, CAE is automatically requested when posting invoices from **Invoicing > Customers > Invoices**. You can also manually request CAE using the **"Request CAE"** button on posted invoices.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    Odoo      │     │    WSAA      │     │   WSFEv1     │
│  (this addon)│────▶│ (Auth Token) │────▶│ (CAE Request)│
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                      │
       │  CMS/PKCS#7        │  Token + Sign        │  CAE + Vto
       │  signed TRA        │                      │
       ▼                    ▼                      ▼
  Private Key +        Login Ticket           Invoice Data
  Certificate          Response               + Authorization
```

### Authentication Flow (WSAA)

1. Build a TRA (Ticket de Requerimiento de Acceso) XML with timestamps in Argentina timezone (-03:00)
2. Sign it with CMS/PKCS#7 using the private key and certificate
3. Send the signed CMS to WSAA `loginCms` endpoint
4. Parse response to extract Token and Sign
5. Cache token until expiration (typically 12 hours)

## ARCA Web Services

| Service | Testing (Homologación) | Production |
|---------|----------------------|------------|
| WSAA | wsaahomo.afip.gov.ar | wsaa.afip.gov.ar |
| WSFEv1 | wswhomo.afip.gov.ar | servicios1.afip.gov.ar |
| WSASS Portal | wsass-homo.afip.gob.ar | (via clave fiscal portal) |

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "No se ha podido interpretar el XML contra el SCHEMA" | Timezone format wrong in TRA XML | Fixed in v1.0 — uses ISO format with colon (-03:00) |
| "Computador no autorizado a acceder al servicio" | wsfe service not authorized | Go to ARCA portal > "Crear autorización a servicio" > select wsfe |
| "El CEE ya posee un TA válido" | Token already active | Not an error — token is cached and valid. Click Test Connection again |
| Upload certificate fails | `not_valid_before_utc` attribute error | Fixed in v1.0 — uses `not_valid_before` (compatible with Odoo 19 cryptography version) |

## License

LGPL-3 - See [LICENSE](LICENSE) file.

## Author

[Leonobitech](https://leonobitech.com)

## Contributing

Contributions are welcome! Please submit pull requests to the [GitHub repository](https://github.com/leonobitech/l10n_ar_arca_edi).
