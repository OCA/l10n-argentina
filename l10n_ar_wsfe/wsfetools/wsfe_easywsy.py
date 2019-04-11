from datetime import datetime
from odoo.exceptions import UserError, ValidationError
from odoo import _, fields

import time
import logging
_logger = logging.getLogger(__name__)


DATE_FORMAT = '%Y-%m-%d'
AFIP_DATE_FORMAT = '%Y%m%d'

try:
    from easywsy import WebService, wsapi
except (ImportError, IOError) as e:

    class wsapi:
        def check(*a, **kw):
            def func(*a, **kw):
                return None
            return func

    WebService = object
    _logger.debug("Cannot import WebService, wsapi from easywsy: \n%s" %
                  repr(e))


class Error:

    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

    def __str__(self):
        return '%s (Err. %s)' % (self.msg, self.code)


class Event:

    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

    def __str__(self):
        return '%s (Evento %s)' % (self.msg, self.code)


class WSFE(WebService):

    # AFIP Requests a (13, 2) format for amounts
    _decimal_precision = 2

    def afip_round(self, data):
        for key, value in data.items():
            if isinstance(value, float):
                data[key] = round(value, self._decimal_precision)
            if isinstance(value, dict):
                self.afip_round(value)
            if isinstance(value, list):
                for item in value:
                    self.afip_round(item)
        return True

    def parse_invoices(self, invoices, first_number=False):
        reg_qty = len(invoices)
        voucher_type = invoices[0]._get_voucher_type()
        pos = invoices[0]._get_pos()
        data = {
            'FECAESolicitar': {
                'FeCAEReq': {
                    'FeCabReq': {
                        'CbteTipo': voucher_type,
                        'PtoVta': pos,
                        'CantReg': reg_qty,
                    },
                    'FeDetReq': {
                        'FECAEDetRequest': [],
                    },
                },
            },
        }
        details_array = data['FECAESolicitar']['FeCAEReq'][
            'FeDetReq']['FECAEDetRequest']
        nn = False
        for inv_index, inv in enumerate(invoices):
            if first_number:
                nn = first_number + inv_index
            inv_data = self.parse_invoice(inv, number=nn, invoices=invoices)
            inv_data['first_of_lot'] = False
            if (first_number and nn == first_number) or len(invoices) == 1:
                inv_data['first_of_lot'] = True
            details_array.append(inv_data)
        return data

    def parse_invoice(self, invoice, number=False, invoices=False):
        invoice.ensure_one()
        if not number:
            number = invoice.split_number()[1]

        date_invoice = datetime.strptime(invoice.date_invoice, '%Y-%m-%d')
        formatted_date_invoice = date_invoice.strftime('%Y%m%d')
        date_due = invoice.date_due and datetime.strptime(
            invoice.date_due, '%Y-%m-%d').strftime('%Y%m%d') or \
            formatted_date_invoice

        # Chequeamos si el concepto es producto,
        # servicios o productos y servicios
        product_service = [l.product_id and l.product_id.type or
                           'consu' for l in invoice.invoice_line_ids]

        service = all([ps == 'service' for ps in product_service])
        products = all([ps == 'consu' or ps == 'product' for
                        ps in product_service])

        # Calculamos el concepto de la factura, dependiendo de las
        # lineas de productos que se estan vendiendo
        concept = None
        if products:
            concept = 1  # Productos
        elif service:
            concept = 2  # Servicios
        else:
            concept = 3  # Productos y Servicios

        doc_type = invoice.partner_id.document_type_id and \
            invoice.partner_id.document_type_id.afip_code or '99'
        doc_num = (invoice.partner_id.vat or '0') if doc_type != '99' else '0'

        company_id = invoice.env.user.company_id
        company_currency_id = company_id.currency_id

        ars_cur = invoice.env.ref('base.ARS')
        if invoice.currency_id == ars_cur:
            currency_code = 'PES'
        else:
            currency_code = invoice.get_currency_code()
        # Cotizacion
        invoice_rate = 1.0
        if invoice.currency_id.id != company_currency_id.id:
            invoice_rate = invoice.currency_rate

        iva_values = self.get_vat_array(invoice)

        detail = {
            'invoices': invoices,
            'invoice': invoice,
            'CbteDesde': number,
            'CbteHasta': number,
            'CbteFch': date_invoice.strftime('%Y%m%d'),
            'Concepto': concept,
            'DocNro': doc_num,
            'DocTipo': doc_type,
            'FchServDesde': False,
            'FchServHasta': False,
            'FchVtoPago': False,
            'MonId': currency_code,
            'MonCotiz': invoice_rate,
        }

        detail.update(iva_values)

        if concept in [2, 3]:
            detail.update({
                'FchServDesde': formatted_date_invoice,
                'FchServHasta': formatted_date_invoice,
                'FchVtoPago': date_due,
            })
        if not hasattr(self.data, 'sent_invoices'):
            self.data.sent_invoices = {}
        self.data.sent_invoices[invoice] = detail
        return detail

    def get_vat_array(self, invoice, retry=False):
        invoice.ensure_one()
        conf = invoice.get_ws_conf()

        afip_taxes = conf.vat_tax_ids.mapped('tax_id')
        not_found_tax = invoice.tax_line_ids.filtered(
            lambda x: x.amount and x.tax_id not in afip_taxes)
        if not_found_tax:
            err = _("Taxes `%s` are not configured in WSFE!") % \
                (", ").join(not_found_tax.mapped('tax_id.name'))
            raise ValidationError(_("Error!\n") + err)

        # Procesamos las taxes

        vat_dict = {}
        for tax_line in invoice.tax_line_ids.filtered(lambda x: x.amount):
            afip_tax = conf.vat_tax_ids.filtered(
                lambda x: x.tax_id == tax_line.tax_id)
            if not afip_tax:
                continue
            # This should be a constraint in wsfe.tax.codes
            afip_tax.ensure_one()
            code = int(afip_tax.code)
            if code not in vat_dict:
                vat_dict[code] = {
                    'Importe': tax_line.amount,
                    'BaseImp': tax_line.base,
                }
            else:
                vat_dict[code]['Importe'] += tax_line.amount
                vat_dict[code]['BaseImp'] += tax_line.base

        vat_array = [{**{'Id': code},
                      **vals} for code, vals in vat_dict.items()]

        vat_tax_amount = sum([x['Importe'] for x in vat_dict.values()])
        vat_base_amount = sum([x['BaseImp'] for x in vat_dict.values()])

        tribute_tax_amount = sum([x.amount for x in invoice.tax_line_ids
                                  if x.tax_id not in afip_taxes and
                                  not x.tax_id.is_exempt])
        tribute_base_amount = sum([x.base for x in invoice.tax_line_ids
                                   if x.tax_id not in afip_taxes and
                                   not x.tax_id.is_exempt])

        exempt_operation_amount = invoice.amount_exempt
        no_taxed_amount = invoice.amount_no_taxed

        base_amount = vat_base_amount + tribute_base_amount
        tax_amount = tribute_tax_amount + vat_tax_amount

        total_amount = round(base_amount + no_taxed_amount +
                             exempt_operation_amount +
                             tax_amount, self._decimal_precision)

        invoice.check_invoice_total(total_amount)

        vals = {
            'number': invoice.internal_number,
            'id': invoice.id,
            'ImpIVA': vat_tax_amount,
            'ImpNeto': vat_base_amount,
            'ImpOpEx': exempt_operation_amount,
            'ImpTotal': total_amount,
            'ImpTotConc': no_taxed_amount,
            'ImpTrib': tribute_tax_amount + tribute_base_amount,
            'Iva': {
                'AlicIva': vat_array,
            },
        }
        self.afip_round(vals)
        log = ('Procesando Factura Electronica: %(number)s (id: %(id)s)\n' +
               'Importe Total: %(ImpTotal)s\n' +
               'Importe Neto Gravado: %(ImpNeto)s\n' +
               'Importe IVA: %(ImpIVA)s\n' +
               'Importe Tributos: %(ImpTrib)s\n' +
               'Importe Operaciones Exentas: %(ImpOpEx)s\n' +
               'Importe Neto no Gravado: %(ImpTotConc)s\n' +
               'Array de IVA: %(Iva)s\n') % vals
        _logger.info(log)
        vals.pop('number')
        vals.pop('id')
        return vals

    def get_response_matching_invoice(self, resp):
        inv = False
        for inv, vals in self.data.sent_invoices.items():
            if resp['CbteDesde'] == vals['CbteDesde'] and \
                    resp['CbteFch'] == vals['CbteFch']:
                break
        return inv

    def parse_invoices_response(self, response):
        errores = []
        comprobantes = []

        if 'Errors' in response:
            for e in response.Errors.Err:
                error = '%s (Err. %s)' % (e.Msg, e.Code)
                errores.append(error)

        for det_response in response.FeDetResp.FECAEDetResponse:
            observaciones = []

            if 'Observaciones' in det_response:
                for o in det_response.Observaciones.Obs:
                    observacion = '%s (Err. %s)' % (o.Msg, o.Code)
                    observaciones.append(observacion)

            for det_req in \
                    self.last_request['args'][1].FeDetReq.FECAEDetRequest:
                if det_req['CbteDesde'] == det_response['CbteHasta'] and \
                        det_req['DocNro'] == det_req['DocNro']:
                    MonId = det_req['MonId']
                    MonCotiz = det_req['MonCotiz']
                    ImpTotal = det_req['ImpTotal']
                    break

            comp = {
                'Concepto': det_response.Concepto,
                'DocTipo': det_response.DocTipo,
                'DocNro': det_response.DocNro,
                'CbteDesde': det_response.CbteDesde,
                'CbteHasta': det_response.CbteHasta,
                'CbteFch': det_response.CbteFch,
                'Resultado': det_response.Resultado,
                'CAE': det_response.CAE,
                'CAEFchVto': det_response.CAEFchVto,
                'Observaciones': observaciones,
                'MonId': MonId,
                'MonCotiz': MonCotiz,
                'ImpTotal': ImpTotal,
            }
            invoice = self.get_response_matching_invoice(comp)
            comp['invoice'] = invoice
            comprobantes.append(comp)

        pos = invoice._get_pos()
        res = {
            'Comprobantes': comprobantes,
            'Errores': errores,
            'PtoVta': pos,
            'Resultado': response.FeCabResp.Resultado,
            'Reproceso': response.FeCabResp.Reproceso,
            'CbteTipo': response.FeCabResp.CbteTipo,
            'CantReg': response.FeCabResp.CantReg,
        }
        self.last_request['parse_result'] = res
        invoices_approved = {}

        # Verificamos el resultado de la Operacion
        # Si no fue aprobado
        if res['Resultado'] == 'R':
            msg = ''
            if res['Errores']:
                msg = 'Errores: ' + '\n'.join(res['Errores']) + '\n'
                msg = msg.encode('latin1').decode('utf8')
            if res['Comprobantes'][0]['Observaciones']:
                msg += '\nObservaciones: ' + '\n'.join(
                    res['Comprobantes'][0]['Observaciones'])
                msg = msg.encode('latin1').decode('utf8')

            if invoice._context.get('raise-exception', True):
                raise UserError(_('AFIP Web Service Error\n' +
                                  'La factura no fue aprobada. \n' +
                                  '%s') % msg)

        elif res['Resultado'] == 'A' or res['Resultado'] == 'P':
            for comp in res['Comprobantes']:
                invoice_vals = {}
                inv = comp['invoice']
                if comp['Observaciones']:
                    msg = 'Observaciones: ' + '\n'.join(comp['Observaciones'])

                # Chequeamos que se corresponda con la
                # factura que enviamos a validar
                doc_type = inv.partner_id.document_type_id and \
                    inv.partner_id.document_type_id.afip_code or '99'
                doc_tipo = comp['DocTipo'] == int(doc_type)
                if comp['DocNro'] == 0:
                    doc_num = inv.partner_id.vat in [False, '', '0'] or doc_type == '99'
                else:
                    try:
                        doc_num = bool(int(inv.partner_id.vat))
                    except ValueError:
                        doc_num = False
                cbte = True
                if inv.internal_number:
                    cbte = comp['CbteHasta'] == int(
                        inv.internal_number.split('-')[1])
                else:
                    # TODO: El nro de factura deberia unificarse
                    # para que se setee en una funcion
                    # o algo asi para que no haya posibilidad de que
                    # sea diferente nunca en su formato
                    invoice_vals['internal_number'] = '%04d-%08d' % (
                        res['PtoVta'], comp['CbteHasta'])

                if not all([doc_tipo, doc_num, cbte]):
                    raise UserError(
                        _("WSFE Error!\n") +
                        _("Validated invoice that not corresponds!"))

                if comp['Resultado'] == 'A':
                    invoice_vals['cae'] = comp['CAE']
                    invoice_vals['cae_due_date'] = comp['CAEFchVto']
                    invoices_approved[inv.id] = invoice_vals

        return invoices_approved

    def log_request(self, environment):
        env = environment
        if not hasattr(self, 'last_request'):
            return False
        res = self.last_request['parse_result']
        wsfe_req_obj = env['wsfe.request']
        voucher_type_obj = env['wsfe.voucher_type']
        voucher_type = voucher_type_obj.search(
            [('code', '=', res['CbteTipo'])])
        voucher_type_name = voucher_type.name
        req_details = []
        pos = res['PtoVta']
        for index, comp in enumerate(res['Comprobantes']):

            # Esto es para fixear un bug que al hacer un refund,
            # si fallaba algo con la AFIP
            # se hace el rollback por lo tanto el refund que se estaba
            # creando ya no existe en
            # base de datos y estariamos violando una foreign
            # key contraint. Por eso,
            # chequeamos que existe info de la invoice_id,
            # sino lo seteamos en False
            read_inv = comp['invoice']

            if not read_inv:
                invoice_id = False
            else:
                invoice_id = read_inv.id
                q = """
                SELECT id FROM account_invoice WHERE id = %(id)s
                """
                env.cr.execute(q, {'id': invoice_id})
                # Invoice Failed to create and does not exist in the DB
                if not env.cr.rowcount:
                    invoice_id = False

            det = {
                'name': invoice_id,
                'concept': str(comp['Concepto']),
                'doctype': comp['DocTipo'],  # TODO: Poner aca el nombre del tipo de documento  # noqa
                'docnum': str(comp['DocNro']),
                'voucher_number': comp['CbteHasta'],
                'voucher_date': comp['CbteFch'],
                'amount_total': comp['ImpTotal'],
                'cae': comp['CAE'],
                'cae_duedate': comp['CAEFchVto'],
                'result': comp['Resultado'],
                'currency': comp['MonId'],
                'currency_rate': comp['MonCotiz'],
                'observations': '\n'.join(comp['Observaciones']).encode(
                'latin1').decode('utf8'),
            }

            req_details.append((0, 0, det))

        # Chequeamos el reproceso
        reprocess = False
        if res['Reproceso'] == 'S':
            reprocess = True

        errors = '\n'.join(res['Errores']).encode('latin1').decode('utf8')
        vals = {
            'voucher_type': voucher_type_name,
            'nregs': len(res['Comprobantes']),
            'pos_ar': '%04d' % pos,
            'date_request': time.strftime('%Y-%m-%d %H:%M:%S'),
            'result': res['Resultado'],
            'reprocess': reprocess,
            'errors': errors,
            'detail_ids': req_details,
        }

        return wsfe_req_obj.create(vals)

    def send_invoice(self, invoice, first_number=False):
        """
        A mask for send_invoices
        """
        return self.send_invoices(invoice, first_number=first_number)

    def auth_decoy(self):
        auth = {
            'Token': 'T',
            'Sign': 'S',
            'Cuit': 'C',
        }
        self.login('Auth', auth)

    def send_invoices(self, invoices, first_number=False, conf=False):
        invoices.complete_date_invoice()
        data = self.parse_invoices(invoices, first_number=first_number)
        self.auth_decoy()
        self.add(data)
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
            auth_instance = getattr(self.data.FECAESolicitar,
                                    self.auth._element_name)
            for k, v in self.auth.attrs.items():
                setattr(auth_instance, k, v)
        _logger.debug(self.data.FECAESolicitar)
        response = self.request('FECAESolicitar')
        approved = self.parse_invoices_response(response)
        return approved

###############################################################################

    def _get_errors(self, result):
        errors = []
        if 'Errors' in result:
            for error in result.Errors.Err:
                error = Error(error.Code, error.Msg)
                errors.append(error)
        return errors

    def _get_events(self, result):
        events = []
        if 'Events' in result:
            for event in result.Events.Evt:
                event = Event(event.Code, event.Msg)
                events.append(event)
        return events

    def check_errors(self, res, raise_exception=True):
        msg = ''
        if 'errors' in res:
            errors = [error.msg for error in res['errors']]
            err_codes = [str(error.code) for error in res['errors']]
            msg = ' '.join(errors)
            msg = msg + ' Codigo/s Error:' + ' '.join(err_codes)

            if msg != '' and raise_exception:
                raise UserError(_('WSFE Error!\n') + msg)
        return msg

    def check_observations(self, res):
        msg = ''
        if 'observations' in res:
            observations = [obs.msg for obs in res['observations']]
            obs_codes = [str(obs.code) for obs in res['observations']]
            msg = ' '.join(observations)
            msg = msg + ' Codigo/s Observacion:' + ' '.join(obs_codes)

            # Escribimos en el log del cliente web
            _logger.info(msg)
        return msg

    def parse_response(self, result):
        res = {}
        # Obtenemos Errores y Eventos
        errors = self._get_errors(result)
        if len(errors):
            res['errors'] = errors

        events = self._get_events(result)
        if len(events):
            res['events'] = events

        res['response'] = result
        self.check_errors(res)
        self.check_observations(res)
        return res

###############################################################################
# AFIP Data Validation Methods According to:
# http://afip.gob.ar/fe/documentos/manual_desarrollador_COMPG_v2_11.pdf

    NATURALS = ['CantReg', 'CbteTipo', 'PtoVta', 'DocTipo',
                'CbteHasta', 'CbteNro', 'Id']

    POSITIVE_REALS = ['ImpTotal', 'ImpTotConc', 'ImpNeto', 'ImpOpEx', 'ImpIVA',
                      'ImpTrib', 'BaseImp', 'Importe']

    STRINGS = ['MonId']

    @wsapi.check(['DocNro'], reraise=True, sequence=20)
    def validate_docnro(val, invoice, DocTipo):
        tin_type = int(DocTipo)
        if tin_type != 99:
            tin_number = int(val)
        else:
            tin_number = val
        if invoice.denomination_id.name == 'B':
            if tin_type != 99 and not tin_number:
                return False
            if invoice.amount_total >= 5000:
                if not tin_number:
                    return False
            else:
                if tin_type == 99 and tin_number != '0':
                    return False
        if invoice.denomination_id.name == 'A':
            if not int(val):
                return False
        return True

    @wsapi.check(['CbteDesde'], reraise=True, sequence=20)
    def validate_invoice_number(val, invoice, invoices, first_of_lot=True):
        if first_of_lot:
            conf = invoice.get_ws_conf()
            fe_next_number = invoice._get_next_wsfe_number(conf=conf)

            # Si es homologacion, no hacemos el chequeo del numero
            if not conf.homologation:
                if int(fe_next_number) != int(val):
                    try:
                        sync_invs = []
                        invoices.env.cr.rollback()
                        invoices.refresh()
                        massive_sync_wiz = invoice.env[
                            'wsfe.massive.sinchronize']
                        vtype = invoice.env['wsfe.voucher_type'].search(
                            [('code', '=', int(invoice._get_voucher_type()))])
                        pos = invoice.env['pos.ar'].search(
                            [('name', '=', str(invoice._get_pos()))])
                        wiz = massive_sync_wiz.create({
                            'voucher_type': vtype.id,
                            'pos_id': pos.id,
                        })
                        act_window = wiz.sinchronize()
                        if act_window and 'domain' in act_window:
                            ids_domain = [x for x in act_window['domain']
                                          if x[0] == 'id']
                            if len(ids_domain) == 1 and \
                                    len(ids_domain[0]) == 3:
                                sync_ids = ids_domain[0][2]
                                sync_invs = invoices.browse(sync_ids)
                        if sync_invs:
                            invoices = invoices.filtered(
                                lambda x: x not in sync_invs)
                        if len(invoices) > 1:
                            massive_inv_wiz = invoices.env[
                                'account.invoice.confirm']
                            wiz = massive_inv_wiz.create({})
                            ctx = {
                                'active_ids': invoices.ids,
                            }
                            wiz.with_context(ctx).invoice_confirm()
                        else:
                            invoices.action_invoice_open()
                    except Exception as e:
                        sync_invs
                        _logger.error(repr(e))
                    finally:
                        if sync_invs:
                            raise UserError(
                                _("WSFE Info!\n") +
                                _("The current invoice was validated and " +
                                  "other invoices were validated too due to " +
                                  "desynchronization. " +
                                  "\nValidated Invoices:\n" +
                                  "%s") % ("\n").join(
                                      invoices.browse(list(
                                          set(sync_invs.ids +
                                              invoices.ids))).mapped(
                                              'internal_number')))
                        else:
                            raise UserError(
                                _("WSFE Error!\n") +
                                _("The next number in the system [%d] does " +
                                  "not match the one obtained from " +
                                  "AFIP WSFE [%d]") %
                                (int(val), int(fe_next_number)))
        return True

    @wsapi.check(NATURALS)
    def validate_natural_number(val):
        val = int(val)
        if val > 0:
            return True
        return False

    @wsapi.check(POSITIVE_REALS)
    def validate_positive_reals(val):
        if not val or (isinstance(val, float) and val > 0):
            return True
        return False

    @wsapi.check(STRINGS)
    def validate_strings(val):
        if isinstance(val, str):
            return True
        return False

    @wsapi.check(['Concepto'])
    def validate_concept(val):
        if val in [1, 2, 3]:
            return True
        return False

    @wsapi.check(['FchServDesde'])
    def validate_service_from_date(val, Concepto):
        if Concepto not in [2, 3]:
            return True
        datetime.strptime(val, AFIP_DATE_FORMAT)
        return True

    @wsapi.check(['FchServHasta'])
    def validate_service_to_date(val, FchServDesde, Concepto):
        if Concepto not in [2, 3]:
            return True
        datetime.strptime(val, AFIP_DATE_FORMAT)
        if val >= FchServDesde:
            return True
        return False

    @wsapi.check(['FchVtoPago'])
    def validate_service_payment_date(val, invoice, Concepto):
        if Concepto not in [2, 3]:
            return True
        datetime.strptime(val, AFIP_DATE_FORMAT)
        inv_date = invoice.date_invoice or fields.Date.context_today(invoice)
        if val >= inv_date.replace('-', ''):
            return True
        return False

    @wsapi.check(['CbteFch'], reraise=True)
    def validate_invoice_date(val, invoice, Concepto):
        if not val:
            return True
        val_dt = datetime.strptime(val, AFIP_DATE_FORMAT)
        val_odoo_format = val_dt.strftime(DATE_FORMAT)
        last_invoiced_date = invoice.get_last_date_invoice()
        if last_invoiced_date and val_odoo_format < last_invoiced_date:
            raise UserError(
                _('WSFE Error!\n') +
                _('There is another Invoice with a most recent date [%s] ' +
                  'for the same Point of Sale and Denomination.') %
                last_invoiced_date)
        today = fields.Date.context_today(invoice)
        today_dt = datetime.strptime(today, DATE_FORMAT)
        offset = today_dt - val_dt
        if Concepto in [2, 3]:
            if abs(offset.days) > 10:
                raise UserError(
                    _('WSFE Error!\n') +
                    _('Invoice Date difference with today should be less ' +
                      'than 5 days for product sales.'))
        else:
            if abs(offset.days) > 5:
                raise UserError(
                    _('WSFE Error!\n') +
                    _('Invoice Date difference with today should be less ' +
                      'than 5 days for product sales.'))
        return True

    @wsapi.check(['MonCotiz'])
    def validate_currency_rate(val, MonId):
        if MonId == 'PES':
            if val == 1:
                return True
        else:
            if isinstance(val, float):
                return True
        return False
