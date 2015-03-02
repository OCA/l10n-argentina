import logging
import py.test
from datetime import datetime, timedelta

logger = logging.getLogger('afipws')

###############################
# Funciones de test para WSFE #
###############################
#def test_get_argauth(wsfe):
#    """Funcion para testear la creacion de un usuario."""
#    argauth = wsfe.get_argauth() 
#    assert argauth.Token != None
#    assert argauth.Sign != None
#
#def test_get_dummy(wsfe):
#    """Funcion para testear la funcion FEDummy"""
#    result = wsfe.fe_dummy()
#    assert result.appserver == "OK"
#    assert result.dbserver == "OK"
#    assert result.authserver == "OK"

def test_create_invoice(wsfe):
    """Funcion para creacion de factura"""
    # Pedimos el ultimo comprobante
    pto_vta = 1
    tipo_cbte = 1
    cbte_nro = wsfe.fe_recupera_last_CMP_request(pto_vta, tipo_cbte)

    # Creamos un importe total
    importe_neto_gravado = 1.00

    detalles = []
    detalle = {}
    detalle['tipo_doc'] = 80 # Tipo CUIT
    detalle['nro_doc'] = 30697613664 # CUIT Cliente
    detalle['tipo_cbte'] = tipo_cbte # Factura A
    detalle['punto_vta'] = pto_vta
    detalle['cbt_desde'] = cbte_nro+1
    detalle['cbt_hasta'] = cbte_nro+1
    detalle['imp_total'] = importe_neto_gravado*1.21
    detalle['imp_tot_conc'] = 0.00
    detalle['imp_neto'] = importe_neto_gravado
    detalle['impto_liq'] = 0.00
    detalle['impto_liq_rni'] = 0.00
    detalle['imp_op_ex'] = 0.00
    detalle['fecha_cbte'] = datetime.now().strftime('%Y%m%d')
#    detalle['fecha_serv_desde'] = 
#    detalle['fecha_serv_hasta'] = 
#    detalle['fecha_venc_pago'] = (datetime.now()+timedelta(days=30)).strftime('%Y%m%d')
    detalles.append(detalle)

    result = wsfe.fe_aut_request(detalles)

