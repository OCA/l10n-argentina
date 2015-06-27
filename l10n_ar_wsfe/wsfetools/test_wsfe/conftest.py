import sys, os

# HACK para que los modulos se importen correctamente
sys.path.append(os.getcwd())

from wsfe_suds import WSFEv1
from wsfex_suds import WSFEX
from wsaa_suds import WSAA
import pytz

#cuit = 30711339740 # PLOT30710981295
#cuit = 30712145028 # Mundo Press
#cuit = 30712306544 # Eynes
cuit = 30710981295 # E-MIPS Test

# Funcion de creacion de la clase WSFE
def create_test_wsfev1():
#    wsaa = WSAA()
#    wsfev1 = WSFEv1(wsaa, cuit, "https://servicios1.afip.gov.ar/wsfev1/service.asmx?wsdl")


    cert = "/home/skennedy/proyectos/afipws/certs/e-mips_test.crt"
    key = "/home/skennedy/proyectos/afipws/certs/privada.key"
    #cert = "/home/skennedy/proyectos/afipws/certs2014/PLOT/CERTIFICADOWSFE2014_66d9bd3bf64846c3.crt"
    #key = "/home/skennedy/proyectos/afipws/certs2014/PLOT/privada.key"
    wsaaurl_homo = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
    wsaaurl_prod = "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"
    wsaa = WSAA(cert=cert, private_key=key, wsaaurl=wsaaurl_homo, service="wsfe")

    wsfeurl_prod = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?wsdl"
    wsfeurl_homo = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?wsdl" 
    wsfev1 = WSFEv1(wsaa, cuit, wsfeurl=wsfeurl_homo)

    return wsfev1

# Destruccion
def destroy_test_wsfev1():
    pass

# Funcion de creacion de la clase WSFEX
def create_test_wsfex():
    cert = "/home/skennedy/proyectos/afipws/certs/e-mips_test.crt"
    key = "/home/skennedy/proyectos/afipws/certs/privada.key"
    tz = pytz.timezone('America/Argentina/Buenos_Aires') or pytz.utc

    wsaaurl_homo = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"

    wsaa = WSAA(cert=cert, private_key=key, wsaaurl=wsaaurl_homo, service="wsfex", tz=tz)
    wsaa.get_token_and_sign()
    wsfex = WSFEX(cuit, wsaa.token, wsaa.sign, "https://wswhomo.afip.gov.ar/wsfexv1/service.asmx?wsdl")
    return wsfex

# Destruccion
def destroy_test_wsfex():
    pass

# Function Argument para instanciar el objeto WSFE y tenerlo durante toda la sesion
def pytest_funcarg__wsfe(request):
    return request.cached_setup(
             setup=lambda: create_test_wsfe(),
             teardown=lambda val: destroy_test_wsfe(),
             scope="session"
    )

def pytest_funcarg__wsfev1(request):
    return request.cached_setup(
             setup=lambda: create_test_wsfev1(),
             teardown=lambda val: destroy_test_wsfev1(),
             scope="session"
    )

def pytest_funcarg__wsfex(request):
    return request.cached_setup(
             setup=lambda: create_test_wsfex(),
             teardown=lambda val: destroy_test_wsfex(),
             scope="session"
    )
