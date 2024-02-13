from pysimplesoap.client import SimpleXMLElement


def _get_response_info(xml_response):
    return SimpleXMLElement(xml_response)


def get_invoice_number_from_response(xml_response, afip_ws="wsfe"):
    if not xml_response:
        return False
    try:
        xml = _get_response_info(xml_response)
        return int(xml("CbteDesde"))
    except Exception:
        return False
