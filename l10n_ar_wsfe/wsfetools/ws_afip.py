##############################################################################
#   Copyright (c) 2019 Eynes/E-MIPS (www.eynes.com.ar)
#   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
##############################################################################

from odoo import _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


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


class AfipWSError:

    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

    def __str__(self):
        return '%s (Err. %s)' % (self.msg, self.code)


class AfipWSEvent:

    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

    def __str__(self):
        return '%s (Evento %s)' % (self.msg, self.code)


class AfipWS(WebService):

    # AFIP Requests a (13, 2) format for amounts
    _decimal_precision = 2

    def _afip_round(self, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, float):
                    data[key] = round(value, self._decimal_precision)
                if isinstance(value, dict):
                    self._afip_round(value)
                if isinstance(value, list):
                    for item in value:
                        self._afip_round(item)
        elif isinstance(data, (int, float)):
            return round(data, self._decimal_precision)
        return True

    def auth_decoy(self):
        auth = {
            'Token': 'T',
            'Sign': 'S',
            'Cuit': 'C',
        }
        self.login('Auth', auth)

    def _get_errors(self, ws_response):
        raise NotImplementedError

    def _get_events(self, ws_response):
        raise NotImplementedError

    def _validate_errors(self, ws_response, raise_exception=True):
        errors = ws_response.get('errors', [])
        err_data = ["[%s] %s" % (str(error.code), error.msg)
                    for error in errors]
        msg = ("\n").join(err_data)

        if msg and raise_exception:
            raise UserError(_('WSFE Error!\n') + msg)
        return msg

    def _log_observations(self, ws_response):
        observations = ws_response.get('observations', [])
        obs_data = ["[%s] %s" % (str(obs.code), obs.msg)
                    for obs in observations]
        msg = ("\n").join(obs_data)

        # Escribimos en el log del cliente web
        _logger.info(msg)
        return msg

    def parse_response(self, ws_response, raise_exception=True):
        errors = self._get_errors(ws_response)
        events = self._get_events(ws_response)

        res = {
            'errors': errors,
            'events': events,
            'response': ws_response,
        }
        self._validate_errors(res, raise_exception=raise_exception)
        self._log_observations(res)
        return res
