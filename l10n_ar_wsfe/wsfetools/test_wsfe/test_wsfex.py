#from wsfe_suds import Error
import logging
import py.test
from datetime import datetime#, timedelta
#from random import choice, uniform

logger = logging.getLogger('afipws')

#################################
# Funciones de test para WSFEv1 #
#################################
#def test_get_argauth(wsfex):
#    """Funcion para testear la creacion de un usuario."""
#    argauth = wsfex.get_argauth() 
#    print argauth
#    assert argauth.Token != None
#    assert argauth.Sign != None

#def test_get_param_mon(wsfex):
#    """Funcion para testear la creacion de un usuario."""
#    result = wsfex.FEXGetPARAM("MON") 
#    print result

#def test_get_param_cbte_tipo(wsfex):
#    """Funcion para testear la creacion de un usuario."""
#    result = wsfex.FEXGetPARAM("Cbte_Tipo") 
#    print result
#
#def test_get_param_umed(wsfex):
#    """Funcion para testear la creacion de un usuario."""
#    result = wsfex.FEXGetPARAM("UMed") 
#    print result
#
#def test_get_param_ptoventa(wsfex):
#    """Funcion para testear la creacion de un usuario."""
#    result = wsfex.FEXGetPARAM("PtoVenta") 
#    print result
#
#def test_get_param_idiomas(wsfex):
#    """Funcion para testear la creacion de un usuario."""
#    result = wsfex.FEXGetPARAM("Idiomas") 
#    print result
#
#def test_get_param_dst(wsfex):
#    """Funcion para testear la creacion de un usuario."""
#    result = wsfex.FEXGetPARAM("DST_pais") 
#    print result
#
#def test_get_param_incoterms(wsfex):
#    """Funcion para testear la creacion de un usuario."""
#    result = wsfex.FEXGetPARAM("Incoterms") 
#    print result
#
#def test_get_param_dst_cuit(wsfex):
#    """Funcion para testear la creacion de un usuario."""
#    result = wsfex.FEXGetPARAM("DST_CUIT") 
#    print result

def test_get_param_cotizacion(wsfex):
    """Funcion para testear la creacion de un usuario."""
    result = wsfex.FEXGetPARAM("Cbte_Tipo") 
    print result

#def test_get_last_id(wsfex):
#    """."""
#    result = wsfex.FEXGetLast_ID() 
#    print result

def test_invoice_sin_permiso_embarque(wsfex):
    """Funcion para testear la autorizacion de un comprobante."""

    # Obtenemos la ultima factura realizada
    cbte_tipo = 19 # Factura de exportacion

    # Llamamos a la funcion
    pto_venta = 1
    ultimo = wsfex.FEXGetLast_CMP(pto_venta, cbte_tipo)['response']
    print 'Ultimo: ', ultimo
    Id = int(datetime.strftime(datetime.now(), '%Y%m%d%H%M%S'))
    today = datetime.strftime(datetime.now(), '%Y%m%d')

    Cmp = {
        'Id' : Id,
        'Cbte_Tipo' : cbte_tipo,
        'Fecha_cbte' : today,
        'Punto_vta' : pto_venta,
        'Cbte_nro' : ultimo+1,
        'Tipo_expo' : 2, #Exportacion de bienes
        'Permiso_existente' : '',
        'Dst_cmp' : 250, # Tierra del fuego
        'Cliente' : "Juan Carlos SH",
        'Domicilio_cliente' : "Calle ABC 123",
        'Cuit_pais_cliente' : 0,
        'Id_impositivo' : '30710981295',
        'Moneda_Id' : "PES",
        'Moneda_ctz' : 1.000000,
        'Imp_total' : 1000,
        'Idioma_cbte' : 1,
        'Items' : [{
            'Pro_codigo' : '1',
            'Pro_ds' : "Producto exportacion test",
            'Pro_qty' : 1,
            'Pro_umed' : 98,
            'Pro_precio_uni' : 1000,
            'Pro_total_item' : 1000,
            'Pro_bonificacion' : 0,
        }]
    }

##    Cmp = {
##        'Id' : 1,
##        'Cbte_Tipo' : 19,
##        'Fecha_cbte' : '20150301',
##        'Punto_vta' : 1,
##        'Cbte_nro' : 1,
##        'Tipo_expo' : 1, #Exportacion de bienes
##        'Permiso_existente' : "N",
##        'Dst_cmp' : 203, # Argentina
##        'Cliente' : "Juan Carlos SH",
##        'Cuit_pais_cliente' : 50000000016,
##        'Domicilio_cliente' : "Calle ABC 123",
##        'Moneda_Id' : "012",
##        'Moneda_ctz' : 0.51,
##        'Imp_total' : 500,
##        'Idioma_cbte' : 1,
##        'Items' : [{
##            'Pro_codigo' : 'PRO1',
##            'Pro_ds' : "Producto exportacion test",
##            'Pro_qty' : 2,
##            'Pro_umed' : 7,
##            'Pro_precio_uni' : 250,
##            'Pro_bonificacion' : 0,
##            'Pro_total_item' : 500,
##        }]
##    }
#
    res = wsfex.FEXAuthorize(Cmp)
    print res
    return res
