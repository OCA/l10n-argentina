from suds.client import Client

class AlwaysCallable(object):
    """
    Represents a chainable-access object and proxies calls to ClientMock.
    """

    name = None

    def __init__(self, client_cls):
        self._client_cls = client_cls

    def __call__(self, *args, **kwargs):
        try:
            hook = object.__getattribute__(self._client_cls, self.name)
        except AttributeError:
            pass
        else:
            return hook(self._client_cls, *args, **kwargs)

    def __getattr__(self, item):
        new = object.__getattribute__(self, '__class__')(self._client_cls)
        new.name = item
        return new


class ClientMock(Client):
    """
    Abstract mock suds client.
    """

    def __init__(self, url, **kwargs):
        pass

    def __getattr__(self, item):
        return AlwaysCallable(self.__class__)

    def __unicode__(self):
        return 'Client mock'

    def __str__(self):
        return 'Client mock'


class WSAA_Client(ClientMock):
    """
    Mock object that implements remote side services.
    """

    def loginCms(self, cms):
        """
        Stub for remote service.
        """
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<loginTicketResponse version="1">
    <header>
        <source>CN=wsaahomo, O=AFIP, C=AR, SERIALNUMBER=CUIT 33693450239</source>
        <destination>C=ar, O=emips, SERIALNUMBER=CUIT 30710981295, CN=emips</destination>
        <uniqueId>1211656281</uniqueId>
        <generationTime>2015-09-06T15:58:33.806-03:00</generationTime>
        <expirationTime>2015-10-07T03:58:33.806-03:00</expirationTime>
    </header>
    <credentials>
           <token>token_test</token>
        <sign>sign_test</sign>
    </credentials>
</loginTicketResponse>
    """
