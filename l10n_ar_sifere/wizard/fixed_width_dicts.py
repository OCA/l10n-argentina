##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

HEAD_LINES_RET = {
    'codigo_jurisdiccion': {
        'type': 'integer',
        'start_pos': 1,
        'length': 3,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    'cuit': {
        'type': 'string',
        'start_pos': 4,
        'length': 13,
        'alignment': 'right',
        'padding': ' ',
        'required': True
    },
    'fecha_retencion': {
        'type': 'string',
        'start_pos': 17,
        'length': 10,
        'alignment': 'right',
        'padding': ' ',
        'required': True
    },
    'numero_sucursal': {
        'type': 'string',
        'start_pos': 27,
        'length': 4,
        'alignment': 'right',
        'padding': ' ',
        'required': True
    },
    'numero_constancia': {
        'type': 'string',
        'start_pos': 31,
        'length': 16,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    'tipo_comprobante': {
        'type': 'string',
        'start_pos': 47,
        'length': 1,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    'letra_comprobante': {
        'type': 'string',
        'start_pos': 48,
        'length': 1,
        'alignment': 'right',
        'padding': ' ',
        'required': True
    },
    'num_comprobante_original': {
        'type': 'string',
        'start_pos': 49,
        'length': 20,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    'monto_retencion': {
        'type': 'string',
        'start_pos': 69,
        'length': 11,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
}

HEAD_LINES_PER = {
    'codigo_jurisdiccion': {
        'type': 'integer',
        'start_pos': 1,
        'length': 3,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    'cuit': {
        'type': 'string',
        'start_pos': 4,
        'length': 13,
        'alignment': 'right',
        'padding': ' ',
        'required': True
    },
    'fecha_percepcion': {
        'type': 'string',
        'start_pos': 17,
        'length': 10,
        'alignment': 'right',
        'padding': ' ',
        'required': True
    },
    'numero_sucursal': {
        'type': 'string',
        'start_pos': 27,
        'length': 4,
        'alignment': 'right',
        'padding': ' ',
        'required': True
    },
    'numero_constancia': {
        'type': 'string',
        'start_pos': 31,
        'length': 8,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    'tipo_comprobante': {
        'type': 'string',
        'start_pos': 39,
        'length': 1,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    'letra_comprobante': {
        'type': 'string',
        'start_pos': 40,
        'length': 1,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
    'monto_percepcion': {
        'type': 'string',
        'start_pos': 41,
        'length': 11,
        'alignment': 'right',
        'padding': '0',
        'required': True
    },
}
