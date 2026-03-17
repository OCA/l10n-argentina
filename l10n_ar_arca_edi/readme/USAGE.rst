Once the module is configured, electronic invoicing works automatically:

#. Create an invoice from **Invoicing > Customers > Invoices**.
#. Fill in the invoice details (customer, lines, taxes, etc.).
#. Click **Confirm** to post the invoice. The CAE is automatically requested
   from ARCA and assigned to the invoice.
#. The CAE number and expiration date are displayed on the invoice form.

If you need to manually request a CAE for a posted invoice that does not have
one yet, use the **Request CAE** button on the invoice form.

The WSAA authentication token is cached and renewed automatically when it
expires. No manual intervention is required for token management.

Certificate expiration is monitored by a scheduled cron job that sends
notifications before the certificate expires.
