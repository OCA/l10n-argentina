##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import _
from odoo.exceptions import UserError
from odoo.addons.l10n_ar_wsfe.wsfetools.ws_afip import \
    wsapi, AfipWS, AfipWSError, AfipWSEvent

import time
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

DATE_FORMAT = '%Y-%m-%d'
FIP_DATE_FORMAT = '%Y%m%d'


class WSFEX(AfipWS):

    @property
    def voucher_type_str(self):
        return 'homo' in self.ws_url and 'Cbte_Tipo' or 'Tipo_cbte'

    @property
    def voucher_asoc_str(self):
        return 'homo' in self.ws_url and 'Cbte_tipo' or 'CBte_tipo'

    @property
    def voucher_resp_str(self):
        return 'homo' in self.ws_url and 'Cbte_tipo' or 'Tipo_cbte'

    def parse_invoices(self, invoices, number=False):
        if len(invoices) > 1:
            raise UserError(
                _("WSFEX Error!\n") +
                _("You cannot inform more than one invoice to AFIP WSFEX"))
        inv = invoices
        inv.ensure_one()

        company = inv.company_id
        voucher_type_obj = inv.env['wsfe.voucher_type']
        currency_code_obj = inv.env['wsfex.currency.codes']
        uom_code_obj = inv.env['wsfex.uom.codes']

        first_num = number
        Id = int(datetime.strftime(datetime.now(), '%Y%m%d%H%M%S'))
        cbte_nro = 0

        # Obtenemos el numero de comprobante a enviar a la AFIP teniendo en
        # cuenta que inv.number == 000X-00000NN o algo similar.
        if not inv.internal_number:
            if not first_num:
                raise UserError(
                    _("WSFE Error!\n") +
                    _("There is no first invoice number declared!"))
            inv_number = first_num
        else:
            inv_number = inv.internal_number

        if not cbte_nro:
            cbte_nro = inv_number.split('-')[1]
            cbte_nro = int(cbte_nro)
        else:
            cbte_nro = cbte_nro + 1

        date_invoice = datetime.strptime(inv.date_invoice, '%Y-%m-%d')
        formatted_date_invoice = date_invoice.strftime('%Y%m%d')

        cuit_pais = inv.dst_cuit_id and int(inv.dst_cuit_id.code) or 0
        inv_currency_id = inv.currency_id.id
        curr_codes = currency_code_obj.search(
            [('currency_id', '=', inv_currency_id)])

        if curr_codes:
            curr_code = curr_codes[0].code
            curr_rate = company.currency_id.id == inv_currency_id and \
                1.0 or inv.currency_rate
        else:
            raise UserError(
                _("WSFEX Error!\n") +
                _("Currency %s has not code configured") %
                inv.currency_id.name)

        # Items
        items = []
        for i, line in enumerate(inv.invoice_line_ids):
            uom_id = line.uom_id.id
            uom_codes = uom_code_obj.search([('uom_id', '=', uom_id)])
            if not uom_codes:
                raise UserError(
                    _("WSFEX Error!\n") +
                    _("There is no UoM Code defined for %s in line %s")
                    % (line.uom_id.name, line.name))

            uom_code = uom_codes[0].code

            items.append({
                'Pro_codigo': i,  # product_code,
                'Pro_ds': line.name.encode('ascii', errors='ignore').decode(),
                'Pro_qty': line.quantity,
                'Pro_umed': uom_code,
                'Pro_precio_uni': line.price_unit,
                'Pro_total_item': line.price_subtotal,
                'Pro_bonificacion': self._afip_round(
                    line._get_applied_discount()),
            })

        Cmps_asoc = []
        for associated_inv in inv.associated_inv_ids:
            tipo_cbte = voucher_type_obj.get_voucher_type(associated_inv)
            pos, number = associated_inv.internal_number.split('-')
            Cmp_asoc = {
                self.voucher_asoc_str: tipo_cbte,
                'Cbte_punto_vta': int(pos),
                'Cbte_nro': int(number),
            }
            if 'homo' in self.ws_url:
                Cmp_asoc.update({
                    'Cbte_cuit': cuit_pais,
                })

            Cmps_asoc.append(Cmp_asoc)

        # TODO: Agregar permisos
        if inv.export_type_id.code == 1:
            shipping_perm = 'S' and inv.shipping_perm_ids or 'N'
        else:
            shipping_perm = 'S' and inv.shipping_perm_ids or ''

        Cmp = {
            self.voucher_type_str: inv._get_voucher_type(),
            'Punto_vta': inv._get_pos(),
            'invoice_id': inv.id,
            'Id': Id,
            'Fecha_cbte': formatted_date_invoice,
            'Cbte_nro': cbte_nro,
            'Tipo_expo': inv.export_type_id.code,  # Exportacion de bienes
            'Permiso_existente': shipping_perm,
            'Dst_cmp': inv.dst_country_id.code or 200,
            'Cliente': inv.partner_id.name.encode(
                'latin-1', errors='ignore').decode('utf8'),
            'Domicilio_cliente': inv.partner_id.contact_address.encode(
                'latin-1', errors='ignore').decode('utf8').replace('\n', ' '),
            'Cuit_pais_cliente': cuit_pais,
            'Id_impositivo': inv.partner_id.vat,
            'Moneda_Id': curr_code,
            'Moneda_ctz': curr_rate,
            'Imp_total': inv.amount_total,
            'Idioma_cbte': 1,
            'Items': {
                'Item': items,
            }
        }

        # Datos No Obligatorios
        if inv.incoterm_id:
            Cmp['Incoterms'] = inv.incoterm_id.code
            Cmp['Incoterms_Ds'] = inv.incoterm_id.name

        if Cmps_asoc:
            Cmp['Cmps_asoc'] = {
                'Cmp_asoc': Cmps_asoc,
            }
        res = {
            'FEXAuthorize': {
                'Cmp': Cmp,
            },
        }
        if not hasattr(self.data, 'sent_invoices'):
            self.data.sent_invoices = {}
        self.data.sent_invoices[inv] = Cmp

        vals = {
            'number': inv.internal_number,
            'id': inv.id,
            'Imp_total': Cmp['Imp_total'],
            'Cliente': Cmp['Cliente'],
        }
        log = ('Procesando Factura Electronica de ' +
               'Exportación: %(number)s (id: %(id)s)\n' +
               'Cliente: %(Cliente)s\n' +
               'Importe Total: %(Imp_total)s') % vals
        _logger.info(log)
        return res

    def send_invoices(self, invoices, first_number=False, conf=False):
        data = self.parse_invoices(invoices, first_number)
        self.auth_decoy()
        self.add(data, no_check='all')
        if not hasattr(self, 'auth') or not self.auth or \
                self.auth.attrs['Token'] == 'T':
            if not conf:
                conf = invoices.get_ws_conf()
            token, sign = conf.wsaa_ticket_id.get_token_sign()
            auth = {
                'Token': token,
                'Sign': sign,
                'Cuit': conf.cuit
            }
            self.login('Auth', auth)
            auth_instance = getattr(self.data.FEXAuthorize,
                                    self.auth._element_name)
            for k, v in self.auth.attrs.items():
                setattr(auth_instance, k, v)
        _logger.debug(self.data.FEXAuthorize)
        response = self.request('FEXAuthorize')
        parsed_res = self.parse_response(response, raise_exception=False)
        approved = self.parse_invoices_response(parsed_res)
        return approved

    def parse_invoices_response(self, response):
        approved_invoices = {}
        invoice_vals = {}

        self._validate_errors(response, raise_exception=True)

        resp_inv_vals = response['response']
        self.last_request['parse_result'] = resp_inv_vals
        res = resp_inv_vals.FEXResultAuth

        inv = list(self.data.sent_invoices.keys())[0]
        if not inv.internal_number:
            invoice_vals['internal_number'] = '%04d-%08d' % \
                (res['Punto_vta'],
                 res['Cbte_nro'])

        if res['Resultado'] == 'R':
            raise UserError(
                _("La factura no fue aprobada, y AFIP no reportó errores"))

        if res['Resultado'] == 'A':
            invoice_vals['cae'] = res['Cae']
            invoice_vals['cae_due_date'] = res['Fch_venc_Cae']
            approved_invoices[inv.id] = invoice_vals

        return approved_invoices

    def log_request(self, environment):
        env = environment
        if not hasattr(self, 'last_request') or \
                'parse_result' not in self.last_request:
            return False

        wsfe_req_obj = env['wsfe.request']
        voucher_type_obj = env['wsfe.voucher_type']

        response = self.last_request['parse_result']
        res = response.FEXResultAuth
        inv = list(self.data.sent_invoices.keys())[0]

        voucher_type = voucher_type_obj.search(
            [('code', '=', res[self.voucher_resp_str])])
        voucher_type_name = voucher_type.name
        req_details = []
        pos = res['Punto_vta']

        sent_req = self.data.FEXAuthorize.Cmp

        events = self._get_events(response)

        det = {
            'name': inv.id,
            'concept': str(sent_req['Tipo_expo']),
            'doctype': sent_req['Dst_cmp'],
            'docnum': str(sent_req['Cuit_pais_cliente']),
            'voucher_number': res['Cbte_nro'],
            'voucher_date': res['Fch_cbte'],
            'amount_total': sent_req['Imp_total'],
            'cae': res['Cae'],
            'cae_duedate': res['Fch_venc_Cae'],
            'result': res['Resultado'],
            'currency': sent_req['Moneda_Id'],
            'currency_rate': sent_req['Moneda_ctz'],
            'observations': ("\n").join(
                [("[%s] %s" %
                  (ev.code, ev.msg)).encode('latin1').decode('utf8')
                 for ev in events]),
        }

        req_details.append((0, 0, det))

        # Chequeamos el reproceso
        reprocess = False
        if res['Reproceso'] == 'S':
            reprocess = True

        errors = self._get_errors(response)

        errors = ("\n").join(
            [("[%s] %s" %
              (err.code, err.msg)).encode('latin1').decode('utf8')
             for err in errors])
        vals = {
            'voucher_type': voucher_type_name,
            'nregs': 1,
            'pos_ar': '%04d' % pos,
            'date_request': time.strftime('%Y-%m-%d %H:%M:%S'),
            'result': res['Resultado'],
            'reprocess': reprocess,
            'errors': errors,
            'detail_ids': req_details,
        }

        return wsfe_req_obj.create(vals)

###############################################################################

    def _get_errors(self, result):
        errors = []
        if 'FEXErr' in result:
            if result.FEXErr.ErrCode != 0:
                errors = [AfipWSError(result.FEXErr.ErrCode,
                                      result.FEXErr.ErrMsg)]
        return errors

    def _get_events(self, result):
        events = []
        if 'FEXEvents' in result:
            if result.FEXEvents.EventCode != 0:
                events = [AfipWSEvent(result.FEXEvents.EventCode,
                                      result.FEXEvents.EventMsg)]
        return events

###############################################################################

    NATURALS = ['Cbte_nro', 'Id']

    # TODO Validations

    @wsapi.check(NATURALS)
    def validate_natural_number(val):
        val = int(val)
        if val > 0:
            return True
        return False
