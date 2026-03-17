All configuration is done from **Settings \> Invoicing \> ARCA
Electronic Invoicing**.

## Step 1: Create Certificate in Odoo

1.  Go to **Settings \> Invoicing**.
2.  In the **ARCA Electronic Invoicing** section, click **Create
    Certificate**.
3.  Fill in the name (e.g., `MyCompany-Testing`), select the company,
    and choose the environment (testing or production).
4.  Click **Create Certificate**.
5.  Click **Generate Key & CSR** to generate the private key and CSR.

## Step 2: Register Certificate in ARCA Portal

For **testing (homologacion)**:

1.  Login at <https://auth.afip.gob.ar> with your CUIT and clave fiscal.
2.  Search for **WSASS - Autogestion Certificados Homologacion**.
3.  This takes you to the WSASS portal.

For **production**:

1.  Login at <https://auth.afip.gob.ar> with your CUIT and clave fiscal.
2.  Search for **Administracion de Certificados Digitales**.

Once inside the WSASS portal:

1.  Click **Nuevo Certificado** in the left sidebar.
2.  Enter a symbolic name for the DN.
3.  Copy the CSR content from Odoo and paste it in the PKCS#10 field.
4.  Click **Crear DN y obtener certificado**.
5.  Copy the resulting certificate (including the `BEGIN` and `END`
    lines) and save it as a `.crt` file.

## Step 3: Authorize wsfe Service

Still in the WSASS portal:

1.  Click **Crear autorizacion a servicio** in the left sidebar.
2.  Select the DN you created, enter your CUIT as the represented
    entity, and select **wsfe - Facturacion Electronica** as the
    service.
3.  Click **Crear autorizacion de acceso**.

> [!IMPORTANT]
> Without this step, the connection test will fail with "Computador no
> autorizado a acceder al servicio".

## Step 4: Upload Certificate in Odoo

1.  Back in Odoo Settings, click **Upload Certificate**.
2.  Upload the `.crt` file saved from ARCA.
3.  Click **Upload**.

## Step 5: Test Connection

1.  Click **Test Connection**.
2.  A success message confirms the WSAA authentication and shows the
    token expiration time (typically 12 hours).

## Step 6: Configure Sales Journal

1.  Go to **Invoicing \> Configuration \> Journals**.
2.  Open your sales journal.
3.  Enable **Use Documents** and **Is ARCA POS?**.
4.  Set **ARCA POS System** to **Online Invoice** (`RLI_RLM` mode).
5.  Set the **ARCA POS Number** matching your point of sale registered
    in ARCA.
