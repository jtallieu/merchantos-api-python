import os
import sys
import base64
import logging

from MerchantOS.api.lib.connection import Connection
from resources import ResourceAccessor

log = logging.getLogger("MerchantOS.api")


class ApiClient(object):
    BASE_URL = '/API'
    
    def __init__(self, host, token, user_id):
        auth = base64.b64encode("%s:%s" % (user_id, token))
        self._connection = Connection(host, self.BASE_URL, auth)
        
        
    def connection(self):
        pass
    
        
    def __getattr__(self, attrname):
        try:
            return ResourceAccessor(attrname, self._connection)
        except:
            raise AttributeError
        raise AttributeError
            