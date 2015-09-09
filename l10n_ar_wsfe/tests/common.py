from openerp.addons.l10n_ar_wsfe.wsfe_suds import WSFEv1


class WSFE_Client(object):
    """
    Mock object that implements remote side services.
    """

    @classmethod
    def _create_client(self, token, sign):
        import ipdb
        ipdb.set_trace()
        self.token = 'token_test'
        self.sign = 'sign_test'
        return 

    @classmethod
    def fe_dummy(self):
        """
        Stub for remote service.
        """
        return {'response': {'AppServer': "OK",
                             'AuthServer': "OK",
                             'DbServer': "OK"}}
