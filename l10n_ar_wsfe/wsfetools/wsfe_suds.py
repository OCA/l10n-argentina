from suds.client import Client
import urllib2

import logging

# Direcciones de los servicios web
WSFEURLv1_HOMO = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?wsdl"
WSFEURLv1_PROD = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?wsdl"

# TODO: Este seteo nunca se hace por como se importa este archivo
# Por otro lao habria que setear el loglevel desde el config
# del OpenERP
logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.client').setLevel(logging.INFO)
logging.getLogger('suds.transport').setLevel(logging.INFO)
logging.getLogger('suds.xsd.schema').setLevel(logging.INFO)
logging.getLogger('suds.wsdl').setLevel(logging.INFO)


class Error:

    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

    def __str__(self):
        return '%s (Err. %s)' % (self.msg, self.code)


class Event:

    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

    def __str__(self):
        return '%s (Evento %s)' % (self.msg, self.code)


class WSFEv1:

    def __init__(self, cuit, token, sign, wsfeurl=WSFEURLv1_HOMO):
        self.wsfeurl = wsfeurl
        self.connected = True
        self.cuit = cuit
        self.token = token
        self.sign = sign
        self.client = None

        # Creamos el cliente
        self._create_client(token, sign)

    def _create_client(self, token, sign):
        try:
            self.client = Client(self.wsfeurl)
            self.client.set_options(location=self.wsfeurl.replace('?wsdl', ''))
        except urllib2.URLError:
            #logger.warning("WSFE: No hay conexion disponible")
            self.connected = False
            raise Exception('No se puede conectar al servicio WSFE')

        # Creamos el argauth
        if self.connected:
            self.argauth = self.client.factory.create('ns0:FEAuthRequest')
            self.argauth.Cuit = self.cuit
            self.argauth.Token = token
            self.argauth.Sign = sign

        return True

    def _get_errors(self, result):
        errors = []
        if 'Errors' in result:
            for error in result.Errors.Err:
                error = Error(error.Code, error.Msg)
                errors.append(error)
        return errors

    def _get_events(self, result):
        events = []
        if 'Events' in result:
            for event in result.Events.Evt:
                event = Event(event.Code, event.Msg)
                events.append(event)
        return events

    def print_services(self):
        if self.connected:
            print self.client
        return

    def fe_dummy(self):
        result = self.client.service.FEDummy()
        res = {}
        res['response'] = {
                'AppServer': result.AppServer,
                'DbServer': result.DbServer,
                'AuthServer': result.AuthServer}
        return res

    def fe_param_get_tipos_cbte(self):

        # Llamamos a la funcion
        result = self.client.service.FEParamGetTiposCbte(self.argauth)

        res = {}
        # Obtenemos Errores y Eventos
        errors = self._get_errors(result)
        if len(errors):
            res['errors'] = errors

        events = self._get_events(result)
        if len(events):
            res['events'] = events

        if 'ResultGet' in result:
            res['response'] = result.ResultGet.CbteTipo

        return res

    def fe_param_get_tipos_concepto(self):

        # Llamamos a la funcion
        result = self.client.service.FEParamGetTiposConcepto(self.argauth)

        res = {}
        # Obtenemos Errores y Eventos
        errors = self._get_errors(result)
        if len(errors):
            res['errors'] = errors

        events = self._get_events(result)
        if len(events):
            res['events'] = events

        if 'ResultGet' in result:
            res['response'] = result.ResultGet.ConceptoTipo

        return res

    def fe_param_get_tipos_doc(self):

        # Llamamos a la funcion
        result = self.client.service.FEParamGetTiposDoc(self.argauth)

        res = {}
        # Obtenemos Errores y Eventos
        errors = self._get_errors(result)
        if len(errors):
            res['errors'] = errors

        events = self._get_events(result)
        if len(events):
            res['events'] = events

        if 'ResultGet' in result:
            res['response'] = result.ResultGet.DocTipo

        return res

    def fe_param_get_tipos_iva(self):

        # Llamamos a la funcion
        result = self.client.service.FEParamGetTiposIva(self.argauth)

        res = {}
        # Obtenemos Errores y Eventos
        errors = self._get_errors(result)
        if len(errors):
            res['errors'] = errors

        events = self._get_events(result)
        if len(events):
            res['events'] = events

        if 'ResultGet' in result:
            res['response'] = result.ResultGet.IvaTipo

        print res
        return res

    def fe_param_get_tipos_monedas(self):

        # Llamamos a la funcion
        result = self.client.service.FEParamGetTiposMonedas(self.argauth)

        res = {}
        # Obtenemos Errores y Eventos
        errors = self._get_errors(result)
        if len(errors):
            res['errors'] = errors

        events = self._get_events(result)
        if len(events):
            res['events'] = events

        if 'ResultGet' in result:
            res['response'] = result.ResultGet.Moneda

        return res

    def fe_param_get_tipos_opcionales(self):

        # Llamamos a la funcion
        result = self.client.service.FEParamGetTiposOpcional(self.argauth)

        res = {}
        # Obtenemos Errores y Eventos
        errors = self._get_errors(result)
        if len(errors):
            res['errors'] = errors

        events = self._get_events(result)
        if len(events):
            res['events'] = events

        if 'ResultGet' in result:
            res['response'] = result.ResultGet.OpcionalTipo

        return res

    def fe_param_get_tipos_tributos(self):

        # Llamamos a la funcion
        result = self.client.service.FEParamGetTiposTributos(self.argauth)

        res = {}
        # Obtenemos Errores y Eventos
        errors = self._get_errors(result)
        if len(errors):
            res['errors'] = errors

        events = self._get_events(result)
        if len(events):
            res['events'] = events

        if 'ResultGet' in result:
            res['response'] = result.ResultGet.TributoTipo

        return res

    def fe_param_get_ptos_venta(self):

        # Llamamos a la funcion
        result = self.client.service.FEParamGetPtosVenta(self.argauth)

        res = {}
        # Obtenemos Errores y Eventos
        errors = self._get_errors(result)
        if len(errors):
            res['errors'] = errors

        events = self._get_events(result)
        if len(events):
            res['events'] = events

        if 'ResultGet' in result:
            res['response'] = result.ResultGet.PtoVenta

        # Retornamos
        return res

    def fe_param_get_cotizacion(self, moneda_id):

        # Llamamos a la funcion
        result = self.client.service.FEParamGetCotizacion(self.argauth, moneda_id)

        res = {}
        # Obtenemos Errores y Eventos
        errors = self._get_errors(result)
        if len(errors):
            res['errors'] = errors

        events = self._get_events(result)
        if len(events):
            res['events'] = events

        if 'ResultGet' in result:
            res['response'] = result.ResultGet

        return res

    def fe_comp_ultimo_autorizado(self, pto_venta, cbte_tipo):

        # Llamamos a la funcion
        result = self.client.service.FECompUltimoAutorizado(self.argauth, pto_venta, cbte_tipo)

        res = {}
        # Obtenemos Errores y Eventos
        errors = self._get_errors(result)
        if len(errors):
            res['errors'] = errors

        events = self._get_events(result)
        if len(events):
            res['events'] = events

        res['response'] = result.CbteNro

        return res

    # TODO: Implementar FECompConsultar. Estaria bueno para saber si hubo algun
    # tema entre el soft y lo que tiene la AFIP
    def fe_comp_consultar(self, pto_venta, cbte_tipo, cbte_nro):

        # Llamamos a la funcion
        arg = self.client.factory.create('ns0:FECompConsultaReq')
        arg.CbteTipo = cbte_tipo
        arg.CbteNro = cbte_nro
        arg.PtoVta = pto_venta
        result = self.client.service.FECompConsultar(self.argauth, arg)

        res = {}
        # Obtenemos Errores y Eventos
        errors = self._get_errors(result)
        if len(errors):
            res['errors'] = errors

        events = self._get_events(result)
        if len(events):
            res['events'] = events

        res['response'] = result

        return res

    def _prepare_tax_trib(self, tg_lst):
        match_vals = {
            'amount': 'Importe',
            'base': 'BaseImp',
            'code': 'Id'
        }
        res = []
        if not tg_lst:
            return res
        for line in tg_lst:
            new_line = {}
            for key, value in line.iteritems():
                if key not in match_vals:
                    raise Exception(_("Key: %s is not in tribute or tax values" %(key)))
                new_line.update({match_vals[key]: value})
            res.append(new_line)
        return res

    def _prepare_details(self, detail_vals):
        match_vals = {
            'sequence_from': 'CbteDesde',
            'sequence_to': 'CbteHasta',
            'concept': 'Concepto',
            'amount_net': 'ImpNeto',
            'amount_exempt': 'ImpOpEx',
            'amount_net_grab': 'ImpTotConc',
            'amount_trib': 'ImpTrib',
            'amount_iva': 'ImpIVA',
            'total_amount': 'ImpTotal',
            'currency_rate': 'MonCotiz',
            'currency_code': 'MonId',
            'doc_type': 'DocTipo', #El suds deja los tags vacios si es None
            'doc_num': 'DocNro',
            'date': 'CbteFch'
        }
        cond_match = {
            'serv_date_from': 'FchServDesde',
            'serv_date_to': 'FchServHasta',
            'due_payment_date':'FchVtoPago'
        }
        if not detail_vals:
            raise Exception(_("There is not values to send in details"))
        res = {}
        for key, value in match_vals.iteritems():
            if key not in detail_vals:
                raise Exception(_("Key: %s is not in detail values" %(key)))
            res.update({value: detail_vals[key]})
        concept = detail_vals.get('concept', '0')
        if str(concept) in ['2','3']:
            for key, value in cond_match.iteritems():
                if key not in detail_vals:
                    raise Exception(_("Key: %s is not in detail values" %(key)))
                res.update({value: detail_vals[key]})
        tax_lst = detail_vals.get('taxes', [])
        new_tax_lst = self._prepare_tax_trib(tax_lst)
        res.update({'taxes': new_tax_lst})
        trib_lst = detail_vals.get('tributes', [])
        new_tribute_lst = self._prepare_tax_trib(trib_lst)
        res.update({'tributes': new_tribute_lst})
        return res

    def get_multi_doc_CAE(self, pos, voucher_type,  values):
        argcaereq = self.client.factory.create('ns0:FECAERequest')
        # FECAECabRequest
        detail = self._prepare_details(values)
        seq_from = detail.get('CbteDesde')
        seq_to = detail.get('CbteHasta')

        argcaereq.FeCabReq.CantReg = 1
        argcaereq.FeCabReq.PtoVta = pos
        argcaereq.FeCabReq.CbteTipo = voucher_type

        tax_lst = detail.pop('taxes')
        trib_lst = detail.pop('tributes')

        argdetreq = self.client.factory.create('ns0:FECAEDetRequest')

        if tax_lst:
            tax_det_lst = []
            for tax_vals in tax_lst:
                argiva = self.client.factory.create('ns0:AlicIva')
                for key, val in tax_vals.iteritems():
                    argiva[key] = None
                    if key in argiva:
                        argiva[key] = val
                tax_det_lst.append(argiva)
            argdetreq.Iva.AlicIva.append(tax_det_lst)

        if trib_lst:
            trib_det_lst = []
            for trib_vals in trib_lst:
                argtrib = self.client.factory.create('ns0:Tributo')
                for key, val in trib_vals.iteritems():
                    argtrib[key] = None
                    if key not in argtrib:
                        argtrib[key] = val
                    trib_det_lst.append(argtrib)
            argdetreq.Tributos.Tributo.append(trib_det_lst)

        for key, det_val in detail.iteritems():
            if key in argdetreq:
                argdetreq[key] = det_val

        argcaereq.FeDetReq.FECAEDetRequest.append(argdetreq)
        result = self.client.service.FECAESolicitar(self.argauth, argcaereq)

        error_lst = []
        voucher_lst = []

        if 'Errors' in result:
            for e in result.Errors.Err:
                error = '%s (Err. %s)' % (e.Msg, e.Code)
                error_lst.append(error)

        for det_response in result.FeDetResp.FECAEDetResponse:
            observation_lst = []
            voucher = {}

            if 'Observaciones' in det_response:
                for o in det_response.Observaciones.Obs:
                    observation = '%s (Err. %s)' % (o.Msg, o.Code)
                    observation_lst.append(observation)

            voucher['Concepto'] = det_response.Concepto
            voucher['DocTipo'] = det_response.DocTipo
            voucher['DocNro'] = det_response.DocNro
            voucher['CbteDesde'] = det_response.CbteDesde
            voucher['CbteHasta'] = det_response.CbteHasta
            voucher['CbteFch'] = det_response.CbteFch
            voucher['Resultado'] = det_response.Resultado
            voucher['CAE'] = det_response.CAE
            voucher['CAEFchVto'] = det_response.CAEFchVto
            voucher['Observaciones'] = observation_lst
            voucher_lst.append(voucher)

        res = {
            'Comprobantes': voucher_lst,
            'Errores': error_lst,
            'Pos': pos,
            'Resultado': result.FeCabResp.Resultado,
            'Reproceso': result.FeCabResp.Reproceso
        }
        return res

    def fe_CAE_solicitar(self, pto_vta, cbte_tipo, detalles):

        argcaereq = self.client.factory.create('ns0:FECAERequest')
        # print argcaereq

        # FECAECabRequest
        argcaereq.FeCabReq.CantReg = len(detalles)
        argcaereq.FeCabReq.PtoVta = pto_vta
        argcaereq.FeCabReq.CbteTipo = cbte_tipo

        for detalle in detalles:
            arrayIva = []
            arrayTributos = []

            argdetreq = self.client.factory.create('ns0:FECAEDetRequest')

            for k, v in detalle.iteritems():
                if isinstance(v, list):
                    if k == 'Iva':
                        for iva in v:
                            argiva = self.client.factory.create('ns0:AlicIva')
                            for k, v in iva.iteritems():
                                if k in argiva:
                                    argiva[k] = v
                                else:
                                    argiva[k] = None

                            arrayIva.append(argiva)
                            continue
                    elif k == 'Tributos':
                        for trib in v:
                            argtrib = self.client.factory.create('ns0:Tributo')
                            for k, v in trib.iteritems():
                                if k in argtrib:
                                    argtrib[k] = v
                                else:
                                    argtrib[k] = None

                            arrayTributos.append(argtrib)
                            continue
                else:
                    if k in argdetreq:
                        argdetreq[k] = v
                    # else:
                        #argdetreq[k] = None

            if len(arrayIva):
                argdetreq.Iva.AlicIva.append(arrayIva)
            if len(arrayTributos):
                argdetreq.Tributos.Tributo.append(arrayTributos)
            argcaereq.FeDetReq.FECAEDetRequest.append(argdetreq)

        result = self.client.service.FECAESolicitar(self.argauth, argcaereq)

        errores = []
        comprobantes = []

        if 'Errors' in result:
            for e in result.Errors.Err:
                error = '%s (Err. %s)' % (e.Msg, e.Code)
                errores.append(error)

        for det_response in result.FeDetResp.FECAEDetResponse:
            observaciones = []
            comp = {}

            if 'Observaciones' in det_response:
                for o in det_response.Observaciones.Obs:
                    observacion = '%s (Err. %s)' % (o.Msg, o.Code)
                    observaciones.append(observacion)

            comp['Concepto'] = det_response.Concepto
            comp['DocTipo'] = det_response.DocTipo
            comp['DocNro'] = det_response.DocNro
            comp['CbteDesde'] = det_response.CbteDesde
            comp['CbteHasta'] = det_response.CbteHasta
            comp['CbteFch'] = det_response.CbteFch
            comp['Resultado'] = det_response.Resultado
            comp['CAE'] = det_response.CAE
            comp['CAEFchVto'] = det_response.CAEFchVto
            comp['Observaciones'] = observaciones
            comprobantes.append(comp)

        res = {'Comprobantes': comprobantes, 'Errores': errores, 'PtoVta': pto_vta, 'Resultado': result.FeCabResp.Resultado, 'Reproceso': result.FeCabResp.Reproceso}
        return res


# if __name__ == "__main__":
#    wsaa = WSAA()
#    wsfe = WSFE(wsaa, CUIT)
#    wsfe.print_services()
#    #wsfe.fe_recupera_last_CMP_request(1, 1)
#    #wsfe.fe_ult_nro_request()
#    #wsfe.fe_dummy()
#    wsfe.fe_aut_request([])
#    #wsfe.fe_recuperar_qty()
