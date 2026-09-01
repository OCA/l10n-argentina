# For copyright and license notices, see __manifest__.py file in module root
# directory or check the readme files

from lxml import etree


def _get_response_info(xml_response):
    """Parse XML response string to etree Element."""
    if isinstance(xml_response, str):
        xml_response = xml_response.encode("utf-8")
    return etree.fromstring(xml_response)


def get_invoice_number_from_response(xml_response, afip_ws="wsfe"):
    """Extract invoice number (CbteDesde) from AFIP XML response."""
    if not xml_response:
        return False
    try:
        xml = _get_response_info(xml_response)
        # Try with namespace first (AFIP uses namespaces in responses)
        namespaces = {"ar": "http://ar.gov.afip.dif.FEV1/"}
        cbte_desde = xml.xpath("//ar:CbteDesde/text()", namespaces=namespaces)
        if not cbte_desde:
            # Fallback: try without namespace (local-name)
            cbte_desde = xml.xpath("//*[local-name()='CbteDesde']/text()")
        if not cbte_desde:
            # Fallback: try simple xpath without namespace
            cbte_desde = xml.xpath("//CbteDesde/text()")
        if cbte_desde:
            return int(cbte_desde[0])
        return False
    except Exception:
        return False
