##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo.addons.base_report_exporter.utils.fixed_width import FixedWidth

SALES_VOUCHER = {
    "date_voucher": {
        "alignment": "right",
        "length": 8,
        "padding": "0",
        "required": True,
        "start_pos": 1,
        "type": "integer"
    },

    "voucher_type": {
        "alignment": "right",
        "length": 3,
        "padding": "0",
        "required": True,
        "start_pos": 9,
        "type": "integer"
    },

    "pos": {
        "alignment": "right",
        "length": 5,
        "padding": "0",
        "required": True,
        "start_pos": 12,
        "type": "integer"
    },

    "voucher_id": {
        "alignment": "right",
        "length": 20,
        "padding": "0",
        "required": True,
        "start_pos": 17,
        "type": "integer"
    },

    "max_voucher_id": {
        "alignment": "right",
        "length": 20,
        "padding": "0",
        "required": True,
        "start_pos": 37,
        "type": "integer"
    },

    "document_type": {
        "alignment": "right",
        "length": 2,
        "padding": "0",
        "required": True,
        "start_pos": 57,
        "type": "integer"
    },

    "partner_id": {
        "alignment": "right",
        "length": 20,
        "padding": "0",
        "required": True,
        "start_pos": 59,
        "type": "string"
    },

    "partner_name": {
        "alignment": "left",
        "length": 30,
        "padding": " ",
        "required": True,
        "start_pos": 79,
        "type": "string"
    },

    "amount_total": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 109,
        "type": "integer"
    },

    "amount_total_non_net": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 124,
        "type": "integer"
    },

    "amount_non_categ_perception": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 139,
        "type": "integer"
    },

    "amount_exempt_transactions": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 154,
        "type": "integer"
    },

    "amount_perceptions_national_taxes": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 169,
        "type": "integer"
    },

    "amount_gross_income_perceptions": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 184,
        "type": "integer"
    },

    "amount_perceptions_city_taxes": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 199,
        "type": "integer"
    },

    "amount_resident_taxes": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 214,
        "type": "integer"
    },

    "currency_code": {
        "alignment": "left",
        "length": 3,
        "padding": " ",
        "required": True,
        "start_pos": 229,
        "type": "string"
    },

    "change_type": {
        "alignment": "right",
        "length": 10,
        "padding": "0",
        "required": True,
        "start_pos": 232,
        "type": "integer"
    },

    "vat_aliquot_qty": {
        "alignment": "right",
        "length": 1,
        "padding": "0",
        "required": True,
        "start_pos": 242,
        "type": "integer"
    },

    "transaction_code": {
        "alignment": "left",
        "length": 1,
        "padding": " ",
        "required": True,
        "start_pos": 243,
        "type": "string"
    },

    "others": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 244,
        "type": "integer"
    },

    "date_payment_due": {
        "alignment": "right",
        "length": 8,
        "padding": "0",
        "required": True,
        "start_pos": 259,
        "type": "integer"
    },
}

SALES_VOUCHER = FixedWidth(SALES_VOUCHER)

IMPORTATION_PURCHASES = {
    "import_delivery": {
        "alignment": "left",
        "length": 16,
        "padding": " ",
        "required": True,
        "start_pos": 1,
        "type": "string"
    },

    "amount_net": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 17,
        "type": "integer"
    },

    "vat_aliquot": {
        "alignment": "right",
        "length": 4,
        "padding": "0",
        "required": True,
        "start_pos": 32,
        "type": "integer"
    },

    "tax": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 36,
        "type": "integer"
    }
}

IMPORTATION_PURCHASES = FixedWidth(IMPORTATION_PURCHASES)

ALIQOUT_PURCHASES = {
    "voucher_type": {
        "alignment": "right",
        "length": 3,
        "padding": "0",
        "required": True,
        "start_pos": 1,
        "type": "integer"
    },

    "pos": {
        "alignment": "right",
        "length": 5,
        "padding": "0",
        "required": True,
        "start_pos": 4,
        "type": "integer"
    },

    "voucher_id": {
        "alignment": "right",
        "length": 20,
        "padding": "0",
        "required": True,
        "start_pos": 9,
        "type": "integer"
    },

    "document_type_id": {
        "alignment": "right",
        "length": 2,
        "padding": "0",
        "required": True,
        "start_pos": 29,
        "type": "integer"
    },

    "seller_id": {
        "alignment": "right",
        "length": 20,
        "padding": "0",
        "required": True,
        "start_pos": 31,
        "type": "string"
    },

    "amount_net": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 51,
        "type": "integer"
    },

    "vat_aliquot": {
        "alignment": "right",
        "length": 4,
        "padding": "0",
        "required": True,
        "start_pos": 66,
        "type": "integer"
    },

    "amount_tax": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 70,
        "type": "integer"
    },
}

ALIQOUT_PURCHASES = FixedWidth(ALIQOUT_PURCHASES)

ALIQOUT_SALES = {
    "voucher_type": {
        "alignment": "right",
        "length": 3,
        "padding": "0",
        "required": True,
        "start_pos": 1,
        "type": "integer"
    },

    "pos": {
        "alignment": "right",
        "length": 5,
        "padding": "0",
        "required": True,
        "start_pos": 4,
        "type": "integer"
    },

    "voucher_id": {
        "alignment": "right",
        "length": 20,
        "padding": "0",
        "required": True,
        "start_pos": 9,
        "type": "integer"
    },

    "amount_net": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 29,
        "type": "integer"
    },

    "vat_aliquot": {
        "alignment": "right",
        "length": 4,
        "padding": "0",
        "required": True,
        "start_pos": 44,
        "type": "integer"
    },

    "amount_tax": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 48,
        "type": "integer"
    },
}

ALIQOUT_SALES = FixedWidth(ALIQOUT_SALES)

PURCHASES_VOUCHER = {
    "date_voucher": {
        "alignment": "right",
        "length": 8,
        "padding": "0",
        "required": True,
        "start_pos": 1,
        "type": "integer"
    },

    "voucher_type": {
        "alignment": "right",
        "length": 3,
        "padding": "0",
        "required": True,
        "start_pos": 9,
        "type": "integer"
    },

    "pos": {
        "alignment": "right",
        "length": 5,
        "padding": "0",
        "required": True,
        "start_pos": 12,
        "type": "integer"
    },

    "voucher_id": {
        "alignment": "right",
        "length": 20,
        "padding": "0",
        "required": True,
        "start_pos": 17,
        "type": "integer"
    },

    "import_delivery": {
        "alignment": "left",
        "length": 16,
        "padding": " ",
        "required": True,
        "start_pos": 37,
        "type": "string"
    },

    "seller_document_type": {
        "alignment": "right",
        "length": 2,
        "padding": "0",
        "required": True,
        "start_pos": 53,
        "type": "integer"
    },

    "seller_id": {
        "alignment": "right",
        "length": 20,
        "padding": "0",
        "required": True,
        "start_pos": 55,
        "type": "string"
    },

    "seller_name": {
        "alignment": "left",
        "length": 30,
        "padding": " ",
        "required": True,
        "start_pos": 75,
        "type": "string"
    },

    "amount_total": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 105,
        "type": "integer"
    },

    "amount_total_non_net": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 120,
        "type": "integer"
    },

    "amount_exempt_transactions": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 135,
        "type": "integer"
    },

    "amount_perceptions_or_vat_national_taxes": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 150,
        "type": "integer"
    },

    "amount_perceptions_national_taxes": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 165,
        "type": "integer"
    },

    "amount_gross_income_perceptions": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 180,
        "type": "integer"
    },

    "amount_perceptions_city_taxes": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 195,
        "type": "integer"
    },

    "amount_resident_taxes": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 210,
        "type": "integer"
    },

    "currency_code": {
        "alignment": "left",
        "length": 3,
        "padding": " ",
        "required": True,
        "start_pos": 225,
        "type": "string"
    },

    "change_type": {
        "alignment": "right",
        "length": 10,
        "padding": "0",
        "required": True,
        "start_pos": 228,
        "type": "integer"
    },

    "vat_aliquot_qty": {
        "alignment": "right",
        "length": 1,
        "padding": "0",
        "required": True,
        "start_pos": 238,
        "type": "integer"
    },

    "transaction_code": {
        "alignment": "left",
        "length": 1,
        "padding": " ",
        "required": True,
        "start_pos": 239,
        "type": "string"
    },

    "comp_fc": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 240,
        "type": "integer"
    },

    "others": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 255,
        "type": "integer"
    },

    "cuit": {
        "alignment": "right",
        "length": 11,
        "padding": "0",
        "required": True,
        "start_pos": 270,
        "type": "integer"
    },

    "partner_name": {
        "alignment": "left",
        "length": 30,
        "padding": " ",
        "required": True,
        "start_pos": 281,
        "type": "string"
    },

    "vat_assigment": {
        "alignment": "right",
        "length": 15,
        "padding": "0",
        "required": True,
        "start_pos": 311,
        "type": "integer"
    },
}

PURCHASES_VOUCHER = FixedWidth(PURCHASES_VOUCHER)
