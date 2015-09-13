from random import random
from datetime import datetime, timedelta

test_invoices = {}

class WSFE_ConfigTest(object):
    """
    Mock object that implements remote side services.
    """
    @classmethod
    def get_last_voucher(self, pos, voucher_type):
        #invoices = filter(lambda x: x.state in ('open', 'paid'), test_invoices.values())
        return len(test_invoices)-1

    @classmethod
    def get_invoice_CAE_approved(self, pos, voucher_type, details):
#        [{'CbteDesde': 154,
#          'CbteFch': '20150910',
#          'CbteHasta': 154,
#          'Concepto': 1,
#          'DocNro': u'20000000028',
#          'DocTipo': u'80',
#          'ImpIVA': 0.0,
#          'ImpNeto': 0.0,
#          'ImpOpEx': 0.0,
#          'ImpTotConc': 20.0,
#          'ImpTotal': 20.0,
#          'ImpTrib': 0.0,
#          'Iva': [],
#          'MonCotiz': 1,
#          'MonId': 'PES',
#          'Tributos': [],
#          'invoice_id': 23}]

        res = {'Comprobantes': [],
               'Errores': [],
               'PtoVta': 1,
               'Reproceso': 'N',
               'Resultado': 'A'}

        for comp in details:
            CAE = int(random()*(10**14))
            dt = datetime.today() + timedelta(days=10)
            cae_due_date = dt.strftime('%Y%m%d')
            c = {
                'CAE': str(CAE),
                'CAEFchVto': cae_due_date,
                'CbteDesde': comp['CbteDesde'],
                'CbteFch': comp['CbteFch'],
                'CbteHasta': comp['CbteHasta'],
                'Concepto': comp['Concepto'],
                'DocNro': int(comp['DocNro']),
                'DocTipo': int(comp['DocTipo']),
                'Observaciones': [],
                'Resultado': 'A',
            }

        res['Comprobantes'].append(c)
        return res

    @classmethod
    def get_voucher_info(self, pos, voucher_type, number, context={}):

        #validated_invoices = filter(lambda x: x.state in ('open', 'paid'), test_invoices.values())
        #last_invoice = validated_invoices[len(validated_invoices)-1]
        draft_invoices = filter(lambda x: x.state=='draft', test_invoices.values())
        invoice = draft_invoices[0]

        #number = int(invoice.internal_number.split('-')[1])
        CAE = int(random()*(10**14))

        # Fecha Vencimiento CAE
        dt = datetime.today() + timedelta(days=10)
        cae_due_date = dt.strftime('%Y%m%d')

        # Fecha Procesamiento
        dt = datetime.today() - timedelta(hours=4)
        processed_date = dt.strftime('%Y%m%d%H%M%S')

        result = {
            'DocTipo': invoice.partner_id.document_type_id.afip_code,
            'DocNro': int(invoice.partner_id.vat),
            'CbteDesde': number,
            'CbteHasta': number,
            'CbteFch': datetime.strptime(invoice.date_invoice, '%Y-%m-%d').
                            strftime('%Y%m%d'),
            'ImpTotal': invoice.amount_total,
            'ImpTotConc': invoice.amount_no_taxed,
            'ImpNeto':  invoice.amount_taxed,
            'ImpOpEx': invoice.amount_exempt,
            'ImpTrib': 0.0,
            'ImpIVA': invoice.amount_tax,
            'FchServDesde': None,
            'FchServHasta': None,
            'FchVtoPago': None,
            'MonId': "PES",
            'MonCotiz': 1.0,
            'Resultado': 'A',
            'CodAutorizacion': CAE,
            'EmisionTipo': "CAE",
            'FchVto': cae_due_date,
            'FchProceso': processed_date,
            'PtoVta': pos,
            'CbteTipo': voucher_type,
        }

        return result

class WSFE_Client(object):
    """
    Mock object that implements remote side services.
    """

    @classmethod
    def _create_client(self, token, sign):
        self.token = 'token_test'
        self.sign = 'sign_test'
        return 

    @classmethod
    def get_last_voucher(self, pos, voucher_type):
        return 10

    @classmethod
    def fe_dummy(self):
        """
        Stub for remote service.
        """
        return {'response': {'AppServer': "OK",
                             'AuthServer': "OK",
                             'DbServer': "OK"}}
