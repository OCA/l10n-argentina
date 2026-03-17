# Copyright 2026 Leonobitech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch, MagicMock

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import ArcaEdiTestCommon


@tagged("post_install", "-at_install")
class TestWsfeParseCaeResponse(ArcaEdiTestCommon):
    """Test _parse_cae_response() with mock SOAP responses."""

    def _make_approved_response(
        self, cae="74291378046073", cae_due="20260325", resultado="A"
    ):
        """Build a mock FECAESolicitar approved response."""
        obs_mock = MagicMock()
        obs_mock.Code = 10016
        obs_mock.Msg = "Observacion de prueba"

        det = MagicMock()
        det.CAE = cae
        det.CAEFchVto = cae_due
        det.Resultado = resultado
        det.Observaciones = None  # No observations for clean approval

        response = MagicMock()
        response.FeDetResp.FECAEDetResponse = [det]
        response.Errors = None

        return response

    def _make_rejected_response(self):
        """Build a mock FECAESolicitar rejected response."""
        det = MagicMock()
        det.CAE = ""
        det.CAEFchVto = ""
        det.Resultado = "R"
        det.Observaciones = MagicMock()
        obs = MagicMock()
        obs.Code = 10016
        obs.Msg = "El campo CbteDesde no es valido"
        det.Observaciones.Obs = [obs]

        err = MagicMock()
        err.Code = 501
        err.Msg = "Error generico"

        response = MagicMock()
        response.FeDetResp.FECAEDetResponse = [det]
        response.Errors = MagicMock()
        response.Errors.Err = [err]

        return response

    def _make_observed_response(self):
        """Build a mock FECAESolicitar observed (approved with warnings) response."""
        obs = MagicMock()
        obs.Code = 10015
        obs.Msg = "Factura duplicada en el periodo"

        det = MagicMock()
        det.CAE = "74291378046073"
        det.CAEFchVto = "20260325"
        det.Resultado = "A"  # Observed but still approved
        det.Observaciones = MagicMock()
        det.Observaciones.Obs = [obs]

        response = MagicMock()
        response.FeDetResp.FECAEDetResponse = [det]
        response.Errors = None

        return response

    def test_parse_approved_response(self):
        """Approved response returns CAE and result=A."""
        wsfe = self.env["l10n_ar.arca.wsfe"]
        response = self._make_approved_response()
        result = wsfe._parse_cae_response(response)

        self.assertEqual(result["cae"], "74291378046073")
        self.assertEqual(result["cae_due_date"], "20260325")
        self.assertEqual(result["result"], "A")
        self.assertEqual(result["observations"], [])
        self.assertEqual(result["errors"], [])

    def test_parse_rejected_response_raises(self):
        """Rejected response raises UserError with error messages."""
        wsfe = self.env["l10n_ar.arca.wsfe"]
        response = self._make_rejected_response()

        with self.assertRaises(UserError) as cm:
            wsfe._parse_cae_response(response)

        error_msg = str(cm.exception)
        self.assertIn("501", error_msg)
        self.assertIn("10016", error_msg)

    def test_parse_observed_response(self):
        """Observed (approved with warnings) returns CAE and observations."""
        wsfe = self.env["l10n_ar.arca.wsfe"]
        response = self._make_observed_response()
        result = wsfe._parse_cae_response(response)

        self.assertEqual(result["cae"], "74291378046073")
        self.assertEqual(result["result"], "A")
        self.assertEqual(len(result["observations"]), 1)
        self.assertEqual(result["observations"][0]["code"], 10015)
        self.assertIn("duplicada", result["observations"][0]["message"])

    def test_parse_empty_response_raises(self):
        """Empty response (no FeDetResp) raises UserError."""
        wsfe = self.env["l10n_ar.arca.wsfe"]
        response = MagicMock()
        response.FeDetResp = None

        with self.assertRaises(UserError):
            wsfe._parse_cae_response(response)

    def test_parse_none_response_raises(self):
        """None response raises UserError."""
        wsfe = self.env["l10n_ar.arca.wsfe"]
        with self.assertRaises(UserError):
            wsfe._parse_cae_response(None)


@tagged("post_install", "-at_install")
class TestWsfeCheckErrors(ArcaEdiTestCommon):
    """Test _check_wsfe_errors() with various response shapes."""

    def test_check_errors_no_errors(self):
        """Response without Errors attribute does not raise."""
        wsfe = self.env["l10n_ar.arca.wsfe"]
        response = MagicMock(spec=[])  # No Errors attribute
        # Should not raise
        wsfe._check_wsfe_errors(response)

    def test_check_errors_none_errors(self):
        """Response with Errors=None does not raise."""
        wsfe = self.env["l10n_ar.arca.wsfe"]
        response = MagicMock()
        response.Errors = None
        wsfe._check_wsfe_errors(response)

    def test_check_errors_empty_err_list(self):
        """Response with Errors.Err=[] does not raise."""
        wsfe = self.env["l10n_ar.arca.wsfe"]
        response = MagicMock()
        response.Errors = MagicMock()
        response.Errors.Err = []
        wsfe._check_wsfe_errors(response)

    def test_check_errors_single_error_raises(self):
        """Response with one error raises UserError containing code and message."""
        wsfe = self.env["l10n_ar.arca.wsfe"]

        err = MagicMock()
        err.Code = 600
        err.Msg = "No se pudo conectar con el servidor"

        response = MagicMock()
        response.Errors = MagicMock()
        response.Errors.Err = [err]

        with self.assertRaises(UserError) as cm:
            wsfe._check_wsfe_errors(response)

        error_msg = str(cm.exception)
        self.assertIn("600", error_msg)
        self.assertIn("No se pudo conectar", error_msg)

    def test_check_errors_multiple_errors_raises(self):
        """Response with multiple errors raises UserError containing all messages."""
        wsfe = self.env["l10n_ar.arca.wsfe"]

        err1 = MagicMock()
        err1.Code = 501
        err1.Msg = "Error generico"

        err2 = MagicMock()
        err2.Code = 502
        err2.Msg = "Servicio no disponible"

        response = MagicMock()
        response.Errors = MagicMock()
        response.Errors.Err = [err1, err2]

        with self.assertRaises(UserError) as cm:
            wsfe._check_wsfe_errors(response)

        error_msg = str(cm.exception)
        self.assertIn("501", error_msg)
        self.assertIn("502", error_msg)
        self.assertIn("Error generico", error_msg)
        self.assertIn("Servicio no disponible", error_msg)


@tagged("post_install", "-at_install")
class TestWsfeGetClient(ArcaEdiTestCommon):
    """Test _get_client() uses correct URLs per environment."""

    @patch("odoo.addons.l10n_ar_arca_edi.models.l10n_ar_arca_wsfe.Client")
    @patch("odoo.addons.l10n_ar_arca_edi.models.l10n_ar_arca_wsfe.Transport")
    def test_get_client_testing(self, mock_transport, mock_client):
        """Testing environment uses homologacion WSDL URL."""
        wsfe = self.env["l10n_ar.arca.wsfe"]
        wsfe._get_client(self.certificate)

        mock_client.assert_called_once()
        args = mock_client.call_args
        self.assertIn("wswhomo.afip.gov.ar", args[0][0])

    @patch("odoo.addons.l10n_ar_arca_edi.models.l10n_ar_arca_wsfe.Client")
    @patch("odoo.addons.l10n_ar_arca_edi.models.l10n_ar_arca_wsfe.Transport")
    def test_get_client_production(self, mock_transport, mock_client):
        """Production environment uses production WSDL URL."""
        self.certificate.environment = "production"
        wsfe = self.env["l10n_ar.arca.wsfe"]
        wsfe._get_client(self.certificate)

        mock_client.assert_called_once()
        args = mock_client.call_args
        self.assertIn("servicios1.afip.gov.ar", args[0][0])

    @patch("odoo.addons.l10n_ar_arca_edi.models.l10n_ar_arca_wsfe.Client")
    @patch("odoo.addons.l10n_ar_arca_edi.models.l10n_ar_arca_wsfe.Transport")
    def test_get_client_custom_urls(self, mock_transport, mock_client):
        """Custom service_urls parameter overrides default."""
        custom_urls = {
            "testing": "https://custom.test/wsdl",
            "production": "https://custom.prod/wsdl",
        }
        wsfe = self.env["l10n_ar.arca.wsfe"]
        wsfe._get_client(self.certificate, service_urls=custom_urls)

        mock_client.assert_called_once()
        args = mock_client.call_args
        self.assertEqual(args[0][0], "https://custom.test/wsdl")


@tagged("post_install", "-at_install")
class TestWsfeGetAuth(ArcaEdiTestCommon):
    """Test _get_auth() builds the correct Auth dict."""

    def test_get_auth_structure(self):
        """Auth dict contains Token, Sign, and Cuit as integer."""
        wsfe = self.env["l10n_ar.arca.wsfe"]
        WsaaModel = type(self.env["l10n_ar.arca.wsaa"])

        with patch.object(
            WsaaModel,
            "_get_or_refresh_token",
            return_value={"token": "TEST_TOKEN", "sign": "TEST_SIGN"},
        ):
            auth = wsfe._get_auth(self.certificate)

        self.assertEqual(auth["Token"], "TEST_TOKEN")
        self.assertEqual(auth["Sign"], "TEST_SIGN")
        self.assertEqual(auth["Cuit"], 20293188204)
        self.assertIsInstance(auth["Cuit"], int)
