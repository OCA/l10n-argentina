# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2015 E-MIPS (http://www.e-mips.com.ar)
#    Copyright (c) 2015 Eynes (http://www.eynes.com.ar)
#    Copyright (c) 2015 Aconcagua Team (http://www.proyectoaconcagua.com.ar)
#    All Rights Reserved. See AUTHORS for details.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from suds.client import Client
from suds import MethodNotFound
import urllib2
import logging

logger = logging.getLogger('suds.client')
logger.setLevel(logging.DEBUG)
 
WSFEXURLv1_HOMO = "https://wswhomo.afip.gov.ar/wsfex/service.asmx?wsdl"
WSAAURL = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl" # homologacion (pruebas)


class FEXError:
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

    def __str__(self):
        return '%s (Err. %s)' % (self.msg, self.code)

class FEXEvent:
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

    def __str__(self):
        return '%s (Evento %s)' % (self.msg, self.code)


class WSFEX:
    def __init__(self, cuit, token, sign, url=WSFEXURLv1_HOMO):
        self.wsfexurl = url
        self.connected = True
        self.cuit = cuit
        self.token = token
        self.sign = sign

        # Creamos el cliente
        self._create_client(token, sign)
 
    def _create_client(self, token, sign):
        try:
            self.client = Client(self.wsfexurl)
            self.client.set_options(location=self.wsfexurl.replace('?wsdl', ''))
        except urllib2.URLError:
            #logger.warning("WSFE: No hay conexion disponible")
            self.connected = False
            raise Exception, 'No se puede conectar al servicio WSFE'

        # Creamos el argauth
        if self.connected:
            self.argauth = self.client.factory.create('ns0:ClsFEXAuthRequest')
            self.argauth.Cuit = self.cuit
            self.argauth.Token = token
            self.argauth.Sign = sign

    def _get_errors(self, result):
        error = None
        if 'FEXErr' in result:
            if result.FEXErr.ErrCode != 0:
                error = FEXError(result.FEXErr.ErrCode, result.FEXErr.ErrMsg)
        return error

    def _get_events(self, result):
        event = None
        if 'FEXEvents' in result:
            if result.FEXEvents.EventCode != 0:
                event = FEXEvent(result.FEXEvents.EventCode, result.FEXEvents.EventMsg)
        return event

    def print_services(self):
        if self.connected:
            print self.client
        return

    def FEXGetLast_ID(self):

        # Llamamos a la funcion
        result = self.client.service.FEXGetLast_ID(self.argauth)
        logger.debug('Result =>\n %s', result)

        res = {}
        # Obtenemos Errores y Eventos
        error = self._get_errors(result)
        if error:
            res['error'] = error

        event = self._get_events(result)
        if event:
            res['event'] = event

        if 'FEXResultGet' in result:
            res['response'] = result.FEXResultGet

        return res

    # Metodo Recuperador de comprobante
    #def FEXGetCMP(self):

    # Metodo Recuperador ultimo numero de comprobante autorizado
    def FEXGetLast_CMP(self, pto_venta, tipo_cbte):

        # Llamamos a la funcion
        result = self.client.service.FEXGetLast_CMP(self.argauth, pto_venta, tipo_cbte)
        logger.debug('Result =>\n %s', result)

        res = {}
        # Obtenemos Errores y Eventos
        error = self._get_errors(result)
        if error:
            res['error'] = error

        event = self._get_events(result)
        if event:
            res['event'] = event

        if 'FEXResult_LastCMP' in result:
            res['response'] = result.FEXResult_LastCMP.Cbte_nro

        return res

    # Funcion para todos los metodos de Parametros
    # @param_func: Nombre del parametro que se necesita obtener:
    # Disponibles:
    # Metodo codigos de unidades de medida "UMed"
    # Metodo codigos de idiomas "Idiomas"
    # Metodo codigos de paises "DST_pais"
    # Metodo codigos de Incoterms "Incoterms"
    # Metodo codigos de CUIT Paises "DST_CUIT"
    # Metodo cotizacion de moneda "Ctz"
    # Metodo codigos de tipo de comprobantes "Cbte_Tipo"
    def FEXGetPARAM(self, param_func):
        # Llamamos a la funcion
        try:
            result = eval("self.client.service.FEXGetPARAM_"+param_func+"(self.argauth)")
            logger.debug('Result =>\n %s', result)
        except MethodNotFound:
            logger.exception("Metodo no encontrado: %s" % param_func)
            return False

        res = {}
        # Obtenemos Errores y Eventos
        error = self._get_errors(result)
        if error:
            res['error'] = error

        event = self._get_events(result)
        if event:
            res['event'] = event

        if 'FEXResultGet' in result:
            res['response'] = result.FEXResultGet

        return res

    # Metodo verificador de existencia de Permiso/Pais
    #def FEXCheck_Permiso(self):

    # Metodo chequeo servidor
    #def FEXDummy(self):
    def FEXAuthorize(self, Cmp):
        if not self.connected:
            self._create_client()
        
        fexrequest = self.client.factory.create('ns0:ClsFEXRequest')
        for k, v in Cmp.iteritems():
            if k == 'Items':
                continue
            if k in fexrequest:
                fexrequest[k] = v
            else:
                logger.warning("Campo %s no se encuentra en tipo ClsFEXRequest" % k)

        for item in Cmp['Items']:
            feitem = self.client.factory.create('ns0:Item')
            for k, v in item.iteritems():
                if k in feitem:
                    feitem[k] = v
                else:
                    logger.warning("Campo %s no se encuentra en tipo Item" % k)

            fexrequest.Items.Item.append(feitem)

        # Llamamos a la funcion
        result = self.client.service.FEXAuthorize(self.argauth, fexrequest)
        logger.debug('Result =>\n %s', result)

        res = {}
        # Obtenemos Errores y Eventos
        error = self._get_errors(result)
        if error:
            res['error'] = error

        event = self._get_events(result)
        if event:
            res['event'] = event

        if 'FEXResultAuth' in result:
            res['response'] = result.FEXResultAuth

        return res

if __name__ == '__main__':
    from wsaa_suds import WSAA

    cert = "/home/skennedy/proyectos/afipws/certs2012/eynes/cert_eynes.crt"
    key = "/home/skennedy/proyectos/afipws/certs2012/eynes/privada_eynes.key"
    wsaa = WSAA(cert=cert, private_key=key, service="wsfex")
    print wsaa

    wsfex = WSFEX(wsaa, cuit)
    #print wsfex.client
    wsfex.FEXGetLast_ID()

#FEXGetLast_ID
