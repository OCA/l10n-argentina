HEAD_LINES = {

    'type': {
        'type': 'integer',
        'start_pos': 1,
        'length': 1,
        'alignment': 'left',
        'default': 1,
        'padding': ' ',
        'required': False
    },

    'date_invoice': {
        'required': True,
        'type': 'string',
        'start_pos': 2,
        'length': 8,
        'alignment': 'left',
        'padding': ' '
    },

    'voucher_type': {
        'required': True,
        'type': 'string',
        'start_pos': 10,
        'length': 2,
        'alignment': 'right',
        'padding': '0'
    },

    'fiscal_controller': {
        'required': True,
        'type': 'string',
        'start_pos': 12,
        'length': 1,
        'alignment': 'left',
        'padding': ' ',
    },
    
    'pos_ar': {
        'required': True,
        'type': 'string',
        'start_pos': 13,
        'length': 4,
        'alignment': 'left',
        'padding': '0'
    },
    
    'invoice_number': {
        'required': True,
        'type': 'string',
        'start_pos': 17,
        'length': 8,
        'alignment': 'left',
        'padding': '0'
    },
    
    'invoice_number_reg': {
        'required': True,
        'type': 'string',
        'start_pos': 25,
        'length': 8,
        'alignment': 'left',
        'padding': '0'
    },
    
    'cant_hojas': {
        'type': 'string',
        'start_pos': 33,
        'length': 3,
        'alignment': 'left',
        'default': '001',
        'padding': ' ',
        'required': False
    },
    
    'code': {
        'type': 'string',
        'start_pos': 36,
        'length': 2,
        'alignment': 'left',
        'padding': '0',
        'required': True
    },
    
    'number': {
        'type': 'string',
        'start_pos': 38,
        'length': 11,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'partner_name': {
        'type': 'string',
        'start_pos': 49,
        'length': 30,
        'alignment': 'left',
        'padding': ' ',
        'required': True
    },
    
    'total': {
        'type': 'string',
        'start_pos': 79,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'neto_no_gravado': {
        'type': 'string',
        'start_pos': 94,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'neto_gravado': {
        'type': 'string',
        'start_pos': 109,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'impuesto_liquidado': {
        'type': 'string',
        'start_pos': 124,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'impuesto_rni': {
        'type': 'string',
        'start_pos': 139,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'impuesto_op_exentas': {
        'type': 'string',
        'start_pos': 154,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_imp_nacionales': {
        'type': 'string',
        'start_pos': 169,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_iibb': {
        'type': 'string',
        'start_pos': 184,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_municipales': {
        'type': 'string',
        'start_pos': 199,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'impuestos_internos': {
        'type': 'string',
        'start_pos': 214,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'transporte': {
        'type': 'string',
        'start_pos': 229,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'tipo_responsable': {
        'type': 'string',
        'start_pos': 244,
        'length': 2,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
   
    'codigo_moneda': {
        'type': 'string',
        'start_pos': 246,
        'length': 3,
        'alignment': 'left',
        'padding': '0',
        'required': True
    },
    
    'tipo_cambio': {
        'type': 'string',
        'start_pos': 249,
        'length': 10,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'cant_alicuotas_iva': {
        'type': 'string',
        'start_pos': 259,
        'length': 1,
        'alignment': 'left',
        'padding': '0',
        'required': True
    },

    'codigo_operacion': {
        'type': 'string',
        'start_pos': 260,
        'length': 1,
        'alignment': 'left',
        'padding': '0',
        'required': True
    },
    
    'cae': {
        'type': 'string',
        'start_pos': 261,
        'length': 14,
        'alignment': 'left',
        'padding': '0',
        'required': True
    },

    'fecha_vencimiento': {
        'type': 'string',
        'start_pos': 275,
        'length': 8,
        'alignment': 'left',
        'padding': '0',
        'required': True
    },

    'fecha_anulacion': {
        'type': 'string',
        'start_pos': 283,
        'length': 8,
        'alignment': 'left',
        'padding': ' ',
        'default': ' ',
        'required': False
    }
}

HEAD_TYPE2_LINES = {

    'type': {
        'type': 'integer',
        'start_pos': 1,
        'length': 1,
        'alignment': 'left',
        'default': 2,
        'padding': ' ',
        'required': False
    },

    'period': {
        'required': True,
        'type': 'string',
        'start_pos': 2,
        'length': 6,
        'alignment': 'left',
        'padding': ' '
    },

    'padding1': {
        'type': 'string',
        'start_pos': 8,
        'length': 13,
        'alignment': 'left',
        'padding': ' ',
        'default': ' ',
        'required': False
    },

    'amount': {
        'required': True,
        'type': 'integer',
        'start_pos': 21,
        'length': 8,
        'alignment': 'right',
        'padding': '0'
    },
 
    'padding2': {
        'type': 'string',
        'start_pos': 29,
        'length': 17,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },
    
    'company_cuit': {
        'required': True,
        'type': 'string',
        'start_pos': 46,
        'length': 11,
        'alignment': 'left',
        'padding': '0'
    },
    
    'padding3': {
        'type': 'string',
        'start_pos': 57,
        'length': 22,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },
    
    'total': {
        'type': 'string',
        'start_pos': 79,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'neto_no_gravado': {
        'type': 'string',
        'start_pos': 94,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'neto_gravado': {
        'type': 'string',
        'start_pos': 109,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'impuesto_liquidado': {
        'type': 'string',
        'start_pos': 124,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'impuesto_rni': {
        'type': 'string',
        'start_pos': 139,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'impuesto_op_exentas': {
        'type': 'string',
        'start_pos': 154,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_imp_nacionales': {
        'type': 'string',
        'start_pos': 169,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_iibb': {
        'type': 'string',
        'start_pos': 184,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_municipales': {
        'type': 'string',
        'start_pos': 199,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'impuestos_internos': {
        'type': 'string',
        'start_pos': 214,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'padding4': {
        'type': 'string',
        'start_pos': 229,
        'length': 62,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },
}

DETAIL_LINES = {

    'voucher_type': {
        'type': 'integer',
        'start_pos': 1,
        'length': 2,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'fiscal_controller': {
        'required': False,
        'type': 'string',
        'start_pos': 3,
        'length': 1,
        'alignment': 'left',
        'padding': ' ',
        'default': ' '
    },

    'date_invoice': {
        'required': True,
        'type': 'string',
        'start_pos': 4,
        'length': 8,
        'alignment': 'left',
        'padding': '0'
    },
 
    'pos_ar': {
        'required': True,
        'type': 'string',
        'start_pos': 12,
        'length': 4,
        'alignment': 'left',
        'padding': '0'
    },
    
    'invoice_number': {
        'required': True,
        'type': 'string',
        'start_pos': 16,
        'length': 8,
        'alignment': 'left',
        'padding': '0'
    },
    
    'invoice_number_reg': {
        'required': True,
        'type': 'string',
        'start_pos': 24,
        'length': 8,
        'alignment': 'left',
        'padding': '0'
    },
    
    'quantity': {
        'type': 'integer',
        'start_pos': 32,
        'length': 12,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'uom': {
        'type': 'string',
        'start_pos': 44,
        'length': 2,
        'alignment': 'right',
        'padding': ' ',
        'required': True
    },
    
    'price_unit': {
        'type': 'string',
        'start_pos': 46,
        'length': 16,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'bonus_amount': {
        'type': 'string',
        'start_pos': 62,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'adjustment_amount': {
        'type': 'string',
        'start_pos': 77,
        'length': 16,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'subtotal': {
        'type': 'string',
        'start_pos': 93,
        'length': 16,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'iva': {
        'type': 'string',
        'start_pos': 109,
        'length': 4,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'exempt_indicator': {
        'type': 'string',
        'start_pos': 113,
        'length': 1,
        'alignment': 'left',
        'padding': '0',
        'required': True
    },
    
    'annulation': {
        'type': 'string',
        'start_pos': 114,
        'length': 1,
        'alignment': 'left',
        'padding': ' ',
        'required': False,
        'default': ' '
    },
    
    'product_name': {
        'type': 'string',
        'start_pos': 115,
        'length': 75,
        'alignment': 'left',
        'padding': ' ',
        'required': True
    },
}

SALE_LINES = {

    'type': {
        'type': 'integer',
        'start_pos': 1,
        'length': 1,
        'alignment': 'left',
        'default': 1,
        'padding': ' ',
        'required': False
    },

    'date_invoice': {
        'required': True,
        'type': 'string',
        'start_pos': 2,
        'length': 8,
        'alignment': 'left',
        'padding': ' '
    },

    'voucher_type': {
        'required': True,
        'type': 'string',
        'start_pos': 10,
        'length': 2,
        'alignment': 'right',
        'padding': '0'
    },
    
    'fiscal_controller': {
        'type': 'string',
        'start_pos': 12,
        'length': 1,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },

    'pos_ar': {
        'required': True,
        'type': 'string',
        'start_pos': 13,
        'length': 4,
        'alignment': 'left',
        'padding': '0'
    },
    
    'invoice_number': {
        'required': True,
        'type': 'string',
        'start_pos': 17,
        'length': 20,
        'alignment': 'right',
        'padding': '0'
    },
    
    'invoice_number_reg': {
        'required': True,
        'type': 'string',
        'start_pos': 37,
        'length': 20,
        'alignment': 'right',
        'padding': '0'
    },
    
    'code': {
        'type': 'string',
        'start_pos': 57,
        'length': 2,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'number': {
        'type': 'string',
        'start_pos': 59,
        'length': 11,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'partner_name': {
        'type': 'string',
        'start_pos': 70,
        'length': 30,
        'alignment': 'left',
        'padding': ' ',
        'required': True
    },
    
    'total': {
        'type': 'string',
        'start_pos': 100,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'neto_no_gravado': {
        'type': 'string',
        'start_pos': 115,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'neto_gravado': {
        'type': 'string',
        'start_pos': 130,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'alic_iva': {
        'type': 'integer',
        'start_pos': 145,
        'length': 4,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'impuesto_liquidado': {
        'type': 'string',
        'start_pos': 149,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'impuesto_rni': {
        'type': 'string',
        'start_pos': 164,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'impuesto_op_exentas': {
        'type': 'string',
        'start_pos': 179,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_imp_nacionales': {
        'type': 'string',
        'start_pos': 194,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_iibb': {
        'type': 'string',
        'start_pos': 209,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_municipales': {
        'type': 'string',
        'start_pos': 224,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'impuestos_internos': {
        'type': 'string',
        'start_pos': 239,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'tipo_responsable': {
        'type': 'string',
        'start_pos': 254,
        'length': 2,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
   
    'codigo_moneda': {
        'type': 'string',
        'start_pos': 256,
        'length': 3,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'tipo_cambio': {
        'type': 'string',
        'start_pos': 259,
        'length': 10,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'cant_alicuotas_iva': {
        'type': 'string',
        'start_pos': 269,
        'length': 1,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'codigo_operacion': {
        'type': 'string',
        'start_pos': 270,
        'length': 1,
        'alignment': 'left',
        'padding': '0',
        'required': True
    },
    
    'cae': {
        'type': 'string',
        'start_pos': 271,
        'length': 14,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'fecha_vencimiento': {
        'type': 'string',
        'start_pos': 285,
        'length': 8,
        'alignment': 'left',
        'padding': '0',
        'required': True
    },

    'fecha_anulacion': {
        'type': 'string',
        'start_pos': 293,
        'length': 8,
        'alignment': 'left',
        'padding': ' ',
        'default': ' ',
        'required': False
    },
    
    'padding1': {
        'type': 'string',
        'start_pos': 301,
        'length': 75,
        'alignment': 'left',
        'padding': ' ',
        'default': ' ',
        'required': False
    }
}

SALE_TYPE2_LINES = {

    'type': {
        'type': 'integer',
        'start_pos': 1,
        'length': 1,
        'alignment': 'left',
        'default': 2,
        'padding': ' ',
        'required': False
    },

    'period': {
        'required': True,
        'type': 'string',
        'start_pos': 2,
        'length': 6,
        'alignment': 'left',
        'padding': ' '
    },
    
    'padding1': {
        'type': 'string',
        'start_pos': 8,
        'length': 29,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },

    'amount': {
        'required': True,
        'type': 'integer',
        'start_pos': 37,
        'length': 12,
        'alignment': 'right',
        'padding': '0'
    },
    
    'padding2': {
        'type': 'string',
        'start_pos': 49,
        'length': 10,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },
    
    'company_cuit': {
        'required': True,
        'type': 'string',
        'start_pos': 59,
        'length': 11,
        'alignment': 'right',
        'padding': '0'
    },
    
    'padding3': {
        'type': 'string',
        'start_pos': 70,
        'length': 30,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },
    
    'total': {
        'type': 'string',
        'start_pos': 100,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'neto_no_gravado': {
        'type': 'string',
        'start_pos': 115,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'neto_gravado': {
        'type': 'string',
        'start_pos': 130,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'padding4': {
        'type': 'string',
        'start_pos': 145,
        'length': 4,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },
    
    'impuesto_liquidado': {
        'type': 'string',
        'start_pos': 149,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'impuesto_rni': {
        'type': 'string',
        'start_pos': 164,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'impuesto_op_exentas': {
        'type': 'string',
        'start_pos': 179,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_imp_nacionales': {
        'type': 'string',
        'start_pos': 194,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_iibb': {
        'type': 'string',
        'start_pos': 209,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_municipales': {
        'type': 'string',
        'start_pos': 224,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'impuestos_internos': {
        'type': 'string',
        'start_pos': 239,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'padding5': {
        'type': 'string',
        'start_pos': 254,
        'length': 122,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },
}

PURCHASE_LINES = {

    'type': {
        'type': 'integer',
        'start_pos': 1,
        'length': 1,
        'alignment': 'right',
        'default': 1,
        'padding': ' ',
        'required': False
    },

    'date_invoice': {
        'required': True,
        'type': 'string',
        'start_pos': 2,
        'length': 8,
        'alignment': 'right',
        'padding': ' '
    },

    'voucher_type': {
        'required': True,
        'type': 'string',
        'start_pos': 10,
        'length': 2,
        'alignment': 'right',
        'padding': '0'
    },
    
    'fiscal_controller': {
        'type': 'string',
        'start_pos': 12,
        'length': 1,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },

    'pos_ar': {
        'required': True,
        'type': 'string',
        'start_pos': 13,
        'length': 4,
        'alignment': 'right',
        'padding': '0'
    },
    
    'invoice_number': {
        'required': True,
        'type': 'string',
        'start_pos': 17,
        'length': 20,
        'alignment': 'right',
        'padding': '0'
    },
    
    'date_invoice2': {
        'required': True,
        'type': 'string',
        'start_pos': 37,
        'length': 8,
        'alignment': 'right',
        'padding': ' '
    },

    'codigo_aduana': {
        'type': 'string',
        'start_pos': 45,
        'length': 3,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'codigo_destinacion': {
        'type': 'string',
        'start_pos': 48,
        'length': 4,
        'alignment': 'left',
        'padding': ' ',
        'default': ' ',
        'required': False
    },
    
    'numero_despacho': {
        'type': 'string',
        'start_pos': 52,
        'length': 6,
        'alignment': 'right',
        'padding': '0',
        'required': False,
        'default': '0',
    },
    
    'verificador_numero_despacho': {
        'type': 'string',
        'start_pos': 58,
        'length': 1,
        'alignment': 'left',
        'padding': ' ',
        'required': False,
        'default': ' ',
    },
    
    'code': {
        'type': 'string',
        'start_pos': 59,
        'length': 2,
        'alignment': 'left',
        'padding': '0',
        'required': True
    },
    
    'number': {
        'type': 'string',
        'start_pos': 61,
        'length': 11,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'partner_name': {
        'type': 'string',
        'start_pos': 72,
        'length': 30,
        'alignment': 'left',
        'padding': ' ',
        'required': True
    },
    
    'total': {
        'type': 'string',
        'start_pos': 102,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'neto_no_gravado': {
        'type': 'string',
        'start_pos': 117,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'neto_gravado': {
        'type': 'string',
        'start_pos': 132,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'alic_iva': {
        'type': 'integer',
        'start_pos': 147,
        'length': 4,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'impuesto_liquidado': {
        'type': 'string',
        'start_pos': 151,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'impuesto_op_exentas': {
        'type': 'string',
        'start_pos': 166,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'percep_iva': {
        'type': 'string',
        'start_pos': 181,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_imp_nacionales': {
        'type': 'string',
        'start_pos': 196,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_iibb': {
        'type': 'string',
        'start_pos': 211,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_municipales': {
        'type': 'string',
        'start_pos': 226,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'impuestos_internos': {
        'type': 'string',
        'start_pos': 241,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'tipo_responsable': {
        'type': 'string',
        'start_pos': 256,
        'length': 2,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
   
    'codigo_moneda': {
        'type': 'string',
        'start_pos': 258,
        'length': 3,
        'alignment': 'left',
        'padding': ' ',
        'required': True
    },
    
    'tipo_cambio': {
        'type': 'string',
        'start_pos': 261,
        'length': 10,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'cant_alicuotas_iva': {
        'type': 'string',
        'start_pos': 271,
        'length': 1,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'codigo_operacion': {
        'type': 'string',
        'start_pos': 272,
        'length': 1,
        'alignment': 'left',
        'padding': ' ',
        'required': True
    },
    
    'cae': {
        'type': 'string',
        'start_pos': 273,
        'length': 14,
        'alignment': 'left',
        'padding': '0',
        'required': True
    },

    'fecha_vencimiento': {
        'type': 'string',
        'start_pos': 287,
        'length': 8,
        'alignment': 'left',
        'padding': '0',
        'required': True
    },
    
    'padding1': {
        'type': 'string',
        'start_pos': 295,
        'length': 75,
        'alignment': 'left',
        'padding': ' ',
        'default': ' ',
        'required': False
    }
}

PURCHASE_TYPE2_LINES = {

    'type': {
        'type': 'integer',
        'start_pos': 1,
        'length': 1,
        'alignment': 'left',
        'default': 2,
        'padding': ' ',
        'required': False
    },

    'period': {
        'required': True,
        'type': 'string',
        'start_pos': 2,
        'length': 6,
        'alignment': 'right',
        'padding': '0'
    },
    
    'padding1': {
        'type': 'string',
        'start_pos': 8,
        'length': 10,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },

    'amount': {
        'required': True,
        'type': 'integer',
        'start_pos': 18,
        'length': 12,
        'alignment': 'right',
        'padding': '0'
    },
    
    'padding2': {
        'type': 'string',
        'start_pos': 30,
        'length': 31,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },
    
    'company_cuit': {
        'required': True,
        'type': 'string',
        'start_pos': 61,
        'length': 11,
        'alignment': 'left',
        'padding': '0'
    },
    
    'padding3': {
        'type': 'string',
        'start_pos': 72,
        'length': 30,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },
    
    'total': {
        'type': 'string',
        'start_pos': 102,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'neto_no_gravado': {
        'type': 'string',
        'start_pos': 117,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'neto_gravado': {
        'type': 'string',
        'start_pos': 132,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'padding4': {
        'type': 'string',
        'start_pos': 147,
        'length': 4,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },
    
    'impuesto_liquidado': {
        'type': 'string',
        'start_pos': 151,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'importe_op_exentas': {
        'type': 'string',
        'start_pos': 166,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'percep_iva': {
        'type': 'string',
        'start_pos': 181,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_imp_nacionales': {
        'type': 'string',
        'start_pos': 196,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_iibb': {
        'type': 'string',
        'start_pos': 211,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'percep_municipales': {
        'type': 'string',
        'start_pos': 226,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },

    'impuestos_internos': {
        'type': 'string',
        'start_pos': 241,
        'length': 15,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    
    'padding5': {
        'type': 'string',
        'start_pos': 256,
        'length': 114,
        'alignment': 'left',
        'default': ' ',
        'padding': ' ',
        'required': False
    },
}
