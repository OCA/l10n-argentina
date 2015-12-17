from wsfe_suds import Error
import logging
import py.test
from datetime import datetime, timedelta
from random import choice, uniform

logger = logging.getLogger('afipws')

#################################
# Funciones de test para WSFEv1 #
#################################
#def test_get_argauth(wsfe):
#    """Funcion para testear la creacion de un usuario."""
#    argauth = wsfe.get_argauth() 
#    print argauth
#    assert argauth.Token != None
#    assert argauth.Sign != None

def test_get_dummy(wsfev1):
    """Funcion para testear la funcion FEDummy"""
    result = wsfev1.fe_dummy()
    print result
    assert result.AppServer == "OK"
    assert result.DbServer == "OK"
    assert result.AuthServer == "OK"

def test_get_tipos_cbtes(wsfev1):
    """Funcion para testear el servicio de obtencion de tipos de comprobantes"""
    result = wsfev1.fe_param_get_tipos_cbte()
    for ct in result['response']:
        print '***********'
        print ct
        print '***********'

#def test_get_tipos_concepto(wsfev1):
#    """Funcion para testear el servicio de obtencion de tipos de concepto"""
#    result = wsfev1.fe_param_get_tipos_concepto()
#    for c in result['response']:
#        print '***********'
#        print c
#        print '***********'

#def test_get_tipos_doc(wsfev1):
#    """Funcion para testear el servicio de obtencion de tipos de documentos"""
#    result = wsfev1.fe_param_get_tipos_doc()
#    for c in result['response']:
#        print '***********'
#        print c
#        print '***********'

#def test_get_tipos_iva(wsfev1):
#    """Funcion para testear el servicio de obtencion de tipos de documentos"""
#    result = wsfev1.fe_param_get_tipos_iva()
#    for c in result['response']:
#        print '***********'
#        print c
#        print '***********'

#def test_get_tipos_monedas(wsfev1):
#    """Funcion para testear el servicio de obtencion de tipos de documentos"""
#    result = wsfev1.fe_param_get_tipos_monedas()
#    print 'Resultdo de las moneadas: ', result
#    for c in result['response']:
#        print '***********'
#        print c
#        print '***********'
#
#def test_get_tipos_opcional(wsfev1):
#    """Funcion para testear el servicio de obtencion de tipos de datos opcionales"""
#    result = wsfev1.fe_param_get_tipos_opcionales()
#    for c in result:
#        print '***********'
#        print c
#        print '***********'

#def test_get_tipos_tributos(wsfev1):
#    """Funcion para testear el servicio de obtencion de tipos de
#
#       tributos que puede contener un comprobante"""
#    result = wsfev1.fe_param_get_tipos_tributos()
#    for c in result['response']:
#        print '***********'
#        print c
#        print '***********'

#def test_get_ptos_venta(wsfev1):
#    """Funcion para testear el servicio de obtencion de puntos de venta habilitados
#       
#       para CAE y CAEA."""
#    # Esta funcion hace un raise error porque no tiene ptos de venta
#    # Da un mensaje de sin resultados
#    res = wsfev1.fe_param_get_ptos_venta()
#    print res
#    #py.test.raises(Error, "wsfev1.fe_param_get_ptos_venta()")

#def test_get_cotizacion(wsfev1):
#    """Funcion para testear el servicio de cotizacion de moneda"""
#    # Obtenemos una moneda
#    monedas = wsfev1.fe_param_get_tipos_monedas()
#    moneda = choice(monedas)
#    moneda_id = moneda.Id
#    result = None
#
#    # Puede que tenga un problema con las monedas que no tienen
#    # cotizacion. Entonces hay que catchear la exception
#    try:
#        result = wsfev1.fe_param_get_cotizacion(moneda_id)
#    except Error, e:
#        print 'Error=> %s' % e
#        return
#
#    assert result.MonId == moneda_id

def test_get_ultimo_comp(wsfev1):
    """Funcion para testear el servicio de obtencion de ultimo comprobante."""
    import pdb
    pdb.set_trace()
    pto_venta = 4

    # Obtenemos un tipo cbte al azar
    #tipos_cbtes = wsfev1.fe_param_get_tipos_cbte()
    cbte_tipo = 3 #choice(tipos_cbtes)

    # Llamamos a la funcion
    ultimo = wsfev1.fe_comp_ultimo_autorizado(pto_venta, cbte_tipo)
    res = ultimo['response']
#    assert res.PtoVta == pto_venta
#    assert res.CbteTipo == cbte_tipo
#    assert res.CbteNro >= 0
#
    res = wsfev1.fe_comp_consultar(pto_venta, cbte_tipo, res.CbteNro)
    print res
#    #print wsfev1.print_services()

#def test_comp_consultar(wsfev1):
#    """Funcion para testear el servicio de consulta de comprobante."""
#    pto_venta = 4
#    #tipo_comp = 1 # Facturas A
#    #tipo_comp = 6 # Facturas B
#    #tipo_comp = 3 # NC A
#    tipo_comp = 8 # NC B
#
#    ultimo = wsfev1.fe_comp_ultimo_autorizado(pto_venta, tipo_comp)
#    res = ultimo['response']
#
#    print 'Nro Comprobante: ', res.CbteNro
#
#    import time
#    import csv
#    f = open('nca.csv', 'w')
#    wr = csv.writer(f)
#
#    header = ['PtoVta', 'CbteDesde', 'CbteFch', 'CbteTipo', 'CodAutorizacion', 'DocNro', 'DocTipo', 'EmisionTipo', 'FchProceso', 'FchVto', 'ImpNeto', 'ImpIVA', 'ImpTrib', 'ImpOpEx', 'ImpTotConc', 'ImpTotal', 'MonCotiz', 'MonId', 'Resultado']
#
#    wr.writerow(header)
#
#    first, last = 180, 183
#    #for comp in range(1, res.CbteNro+1):
#    for comp in range(first, last+1):
#        time.sleep(0.1)
#        # Llamamos a la funcion
#        cbte = wsfev1.fe_comp_consultar(pto_venta, tipo_comp, comp)
#
#        res = cbte['response']
#
#        row = []
#        row.append(res.ResultGet.PtoVta)
#        row.append(res.ResultGet.CbteDesde)
#        row.append(res.ResultGet.CbteFch)
#        row.append(res.ResultGet.CbteTipo)
#        row.append(res.ResultGet.CodAutorizacion)
#        row.append(res.ResultGet.DocNro)
#        row.append(res.ResultGet.DocTipo)
#        row.append(res.ResultGet.EmisionTipo)
#        row.append(res.ResultGet.FchProceso)
#        row.append(res.ResultGet.FchVto)
#        row.append(res.ResultGet.ImpNeto)
#        row.append(res.ResultGet.ImpIVA)
#        row.append(res.ResultGet.ImpTrib)
#        row.append(res.ResultGet.ImpOpEx)
#        row.append(res.ResultGet.ImpTotConc)
#        row.append(res.ResultGet.ImpTotal)
#        #row.append(res.ResultGet.Iva)
#        row.append(res.ResultGet.MonCotiz)
#        row.append(res.ResultGet.MonId)
#        row.append(res.ResultGet.Resultado)
#
#
#        wr.writerow(row)
#
#    f.close()
#    print res
#    #print wsfev1.print_services()

#def test_invoice(wsfev1):
#    # Obtenemos los tipos de IVA
#    tipos_iva = wsfev1.fe_param_get_tipos_iva()['response']
#    print tipos_iva
#    iva21 = None
#    iva105 = None
#    for iva in tipos_iva:
#        if iva.Desc == '21%':
#            iva21 = iva.Id
#        elif iva.Desc == '10.5%':
#            iva105 = iva.Id 
#
#    # Ponemos un importe neto gravado
#    imp_neto_grav = round(uniform(100, 200), 2)
#    #print 'Importe Neto: ', imp_neto_grav
#
#    # Sobre este calculamos IVA del 21 y del 10.5
#    imponible_105 = round(imp_neto_grav / 3, 2)
#    imponible_21 = round(imp_neto_grav-imponible_105, 2)
#    
#    #print 'Imponible 21%: ', imponible_21
#    #print 'Imponible 10,5%: ', imponible_105
#    #print 'Suma: ', imponible_21+imponible_105
#
#    imp_21 = round(imponible_21*0.21, 2) 
#    imp_105 = round(imponible_105*0.105, 2)
#
#    iva_array = [{'Id': iva21, 'BaseImp': imponible_21, 'Importe': imp_21 },
#                 {'Id': iva105, 'BaseImp': imponible_105, 'Importe': imp_105 }]
#
#    imp_iva = imp_21+imp_105
#    imp_total = imp_neto_grav + imp_iva
#    #print 'Importe 21%: ', imp_21
#    #print 'Importe 10,5%: ', imp_105
#    #print 'Total: ', imp_total
#
#    # Obtenemos la ultima factura realizada
#    tipos_elegir = [1]# [1, 6] 
#    cbte_tipo = choice(tipos_elegir)
#
#    # Llamamos a la funcion
#    pto_venta = 1
#    ultimo = wsfev1.fe_comp_ultimo_autorizado(pto_venta, cbte_tipo)['response']
#    ultimo = ultimo.CbteNro
#    #print 'Ultimo: ', ultimo
#
#    args = {
#        'Concepto' : 1,
#        'DocTipo' : 80,
#        'DocNro' : 30662071, #680,
#        'CbteDesde' : ultimo+1,
#        'CbteHasta' : ultimo+1,
#        'CbteFch' : datetime.now().strftime('%Y%m%d'),
#        'ImpTotal' : imp_total,
#        'ImpTotConc' : 0,
#        'ImpNeto' : imp_neto_grav,
#        'ImpOpEx' : 0,
#        'ImpTrib' : 0,
#        'ImpIVA' : imp_iva,
#        #'FchServDesde' : ,
#        #'FchServHasta' : ,
#        #'FchVtoPago' : 
#        'MonId' : 'PES',
#        'MonCotiz' : 1,
##        'CbtesAsoc' : #Array
#        'Tributos' : None, #Array
#        'Iva' : iva_array, #Array
##        'Opcionales' : #Array
#    }
#
#    detalles = []
#    detalles.append(args)
#
#    res = wsfev1.fe_CAE_solicitar(pto_venta, cbte_tipo, detalles)
#    print res
