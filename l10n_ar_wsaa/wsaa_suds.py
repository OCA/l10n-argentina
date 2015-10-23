from lxml import etree
from datetime import datetime
import time
import sys
import email
import urllib2
from M2Crypto import BIO, SMIME
from suds.client import Client
from xml.sax import SAXParseException
import logging
from openerp.tools.misc import ustr
import pytz

## Configuracion del logger
logger = logging.getLogger('afipws')
logger.setLevel(logging.DEBUG)
#streamH = logging.StreamHandler(sys.stdout)
#streamH.setLevel(logging.DEBUG)
#streamH.setFormatter(formatter)
#logger.addHandler(streamH)


class WSAA:
    def __init__(self, cert, private_key, wsaaurl, service, tz):
        """Init."""
        self.token = None
        self.sign = None
        self.wsaaurl = wsaaurl
        self.service = service
        self.expiration_time = None
        self.ta = None
        self.connected = True
        self.timezone = tz

        try:
            self._create_client()
        except urllib2.URLError, e:
            logger.error("No hay conexion disponible")
            self.connected = False
            raise Exception, 'No se puede conectar con AFIP: %s' % str(e)
        except SAXParseException, e:
            raise Exception, 'WSAA URL malformada: %s' % e.getMessage()
        except Exception, e:
            raise Exception, 'Unknown Error: %s' % e

    def _create_client(self):
        # Creamos el cliente contra la URL
        self.client = Client(self.wsaaurl)

    def _create_tra(self):
        """Funcion para crear el TRA."""
        # Creamos el root
        logger.debug("Creando TRA")
        root = etree.Element('loginTicketRequest')
        doc = etree.ElementTree(root)
        root.set('version', '1.0')

        # Creamos los childs de loginTicketRequest
        header = etree.SubElement(root, 'header')

        # UniqueId
        uniqueid = etree.SubElement(header, 'uniqueId')
        timestamp = int(time.mktime(datetime.now().timetuple()))
        uniqueid.text = str(timestamp)

        # generationTime
        tsgen = datetime.fromtimestamp(timestamp-2400)
        tsgen = pytz.utc.localize(tsgen).astimezone(self.timezone)
        gentime = etree.SubElement(header, 'generationTime')
        gentime.text = tsgen.isoformat()

        # expirationTime
        tsexp = datetime.fromtimestamp(timestamp+14400)
        tsexp = pytz.utc.localize(tsexp).astimezone(self.timezone)
        exptime = etree.SubElement(header, 'expirationTime')
        exptime.text = tsexp.isoformat()

        # service
        serv = etree.SubElement(root, 'service')
        serv.text = self.service

#        try:
#            f = open('tra.xml', 'w')
#            doc.write(f, xml_declaration=True, encoding='UTF-8', pretty_print=True)
#        except Exception, e:
#            print 'No se puede grabar el archivo: %s' % e
#            return None

        logger.debug("TRA Creado")
        return etree.tostring(doc)


    def _sign_tra(self, tra, cert, key):
        """Funcion que firma el tra."""

        # Creamos un buffer a partir del TRA
        buf = BIO.MemoryBuffer(tra)
        key_bio = BIO.MemoryBuffer(key.encode('ascii'))
        cert_bio = BIO.MemoryBuffer(cert.encode('ascii'))

        # Firmamos el TRA
        s = SMIME.SMIME()
        s.load_key_bio(key_bio, cert_bio)
        p7 = s.sign(buf, 0)
        out = BIO.MemoryBuffer()
        s.write(out, p7)

        # Extraemos la parte que nos interesa
        msg = email.message_from_string(out.read())
        for part in msg.walk():
            filename = part.get_filename()
            if filename == "smime.p7m":
                logger.debug("TRA Firmado")
                return part.get_payload(decode=False)


    def _call_wsaa(self, cms):
        """ Funcion para llamar al WSAA y loguearse """

        # Si no esta conectado, probamos conectar nuevamente
        if not self.connected:
            try:
                self._create_client()
            except urllib2.URLError, e:
                logger.warning("No hay conexion disponible")
                self.connected = False
                raise Exception, 'No hay conexion: %s' % e

        # Llamamos a loginCms y obtenemos el resultado
        logger.debug("Llamando a loginCms:\n%s", cms)
        try:
            result = self.client.service.loginCms(cms)
        except Exception, e:
            logger.exception("Excepcion al llamar a loginCms")
            raise Exception, 'Exception al autenticar: %s' % ustr(e)

        self.ta = result
        return result

    def parse_ta(self, ta=None):
        if not ta:
            ta = self.ta
            if not ta:
                return

        # Quitamos la declaracion de XML
        tas = ta.split('\n')
        if tas[0].find("?xml"):
            ta = '\n'.join(tas[1:])

        # Parseamos el resultado
        root = etree.XML(ta)

        # Buscamos el expirationTime
        header = root.find('header')
        exptime = header.find('expirationTime')
        exptime_iso = exptime.text[0:exptime.text.rfind('-')]
        self.expiration_time = datetime.strptime(exptime_iso, '%Y-%m-%dT%H:%M:%S.%f')

         # Si no expiro, obtenemos el token y el sign
        cred = root.find('credentials')
        self.token =  cred.find('token').text
        self.sign =  cred.find('sign').text

        return True

    # TODO: Agregar una flag de force para tomarlo igual
    # TODO: Hacer chequeo de errores
    def get_token_and_sign(self, cert, key, force=True):
        # Primero chequeamos si ya tenemos un token
        if not force:
            if self.ta and self.expiration_time and self.token and self.sign:
                # Si todavia no expiro el que tenemos, lo retornamos
                if datetime.now() < self.expiration_time:
                    return self.token, self.sign

        tra = self._create_tra()
        cms = self._sign_tra(tra, cert, key)
        try:
            self._call_wsaa(cms)
        except Exception, e:
            raise e

        self.parse_ta(self.ta)
        return True

CERT = "/home/skennedy/proyectos/afipws/certs2012/eynes/cert_eynes.crt"        # El certificado X.509 obtenido de Seg. Inf.
PRIVATEKEY = "/home/skennedy/proyectos/afipws/certs2012/eynes/privada_eynes.key"  # La clave privada del certificado CERT
WSAAURL = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl" # homologacion (pruebas)
#WSAAURL="https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"

if __name__ == '__main__':
    wsaa = WSAA(CERT, PRIVATEKEY, WSAAURL, "wsfe")
    token = None
    sign = None
    expiration_time = None
    try:
        # Se puede llamar a get_token_and_sign o pasarle un TA
        # anterior a wsaa.parse_ta
        wsaa.get_token_and_sign()
        token = wsaa.token
        expiration_time = wsaa.expiration_time
        sign = wsaa.sign
    except Exception, e:
        print e

    # Vemos si ya expiro
    if datetime.now() > expiration_time:
        print "Certificado expirado"

    print 'Token: ', token
    print 'Sign: ', sign
    print 'Expiration Time: ', expiration_time.strftime("%d/%m/%Y %H:%M:%S")
