All configuration is done from **Settings > Invoicing > ARCA Electronic
Invoicing**.

Step 1: Create Certificate in Odoo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. Go to **Settings > Invoicing**.
#. In the **ARCA Electronic Invoicing** section, click **Create Certificate**.
#. Fill in the name (e.g., ``MyCompany-Testing``), select the company, and
   choose the environment (testing or production).
#. Click **Create Certificate**.
#. Click **Generate Key & CSR** to generate the private key and CSR.

Step 2: Register Certificate in ARCA Portal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For **testing (homologacion)**:

#. Login at https://auth.afip.gob.ar with your CUIT and clave fiscal.
#. Search for **WSASS - Autogestion Certificados Homologacion**.
#. This takes you to the WSASS portal.

For **production**:

#. Login at https://auth.afip.gob.ar with your CUIT and clave fiscal.
#. Search for **Administracion de Certificados Digitales**.

Once inside the WSASS portal:

#. Click **Nuevo Certificado** in the left sidebar.
#. Enter a symbolic name for the DN.
#. Copy the CSR content from Odoo and paste it in the PKCS#10 field.
#. Click **Crear DN y obtener certificado**.
#. Copy the resulting certificate (including the ``BEGIN`` and ``END`` lines)
   and save it as a ``.crt`` file.

Step 3: Authorize wsfe Service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Still in the WSASS portal:

#. Click **Crear autorizacion a servicio** in the left sidebar.
#. Select the DN you created, enter your CUIT as the represented entity, and
   select **wsfe - Facturacion Electronica** as the service.
#. Click **Crear autorizacion de acceso**.

.. important::

   Without this step, the connection test will fail with
   "Computador no autorizado a acceder al servicio".

Step 4: Upload Certificate in Odoo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. Back in Odoo Settings, click **Upload Certificate**.
#. Upload the ``.crt`` file saved from ARCA.
#. Click **Upload**.

Step 5: Test Connection
~~~~~~~~~~~~~~~~~~~~~~~

#. Click **Test Connection**.
#. A success message confirms the WSAA authentication and shows the token
   expiration time (typically 12 hours).

Step 6: Configure Sales Journal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. Go to **Invoicing > Configuration > Journals**.
#. Open your sales journal.
#. Enable **Use Documents** and **Is ARCA POS?**.
#. Set **ARCA POS System** to **Online Invoice** (``RLI_RLM`` mode).
#. Set the **ARCA POS Number** matching your point of sale registered in ARCA.
