"""
Connection Module

Handles put and get operations to the Bigcommerce REST API
"""
import sys
import time
import urllib
import logging
import simplejson
from urlparse import urlparse
from pprint import pprint, pformat
from httplib import HTTPSConnection, HTTPException

 
log = logging.getLogger("MerchantOS.con")

class EmptyResponseWarning(HTTPException):
    pass


class Connection():
    """
    Connection class manages the connection to the Bigcommerce REST API.
    """
    
    def __init__(self, host, base_url, auth):
        """
        Constructor
        
        On creation, an initial call is made to load the mappings of resources to URLS
        """
        self.host = host
        self.base_url = base_url
        self.resource_base_url = "%s/Account" % self.base_url
        self.auth = auth
        self.account_id = ""
        
        log.info("API Host: %s/%s" % (self.host, self.base_url))
        log.debug("Accepting json, auth: Basic %s" % self.auth)
        self.__headers = {"Authorization": "Basic %s" % self.auth,
                        "Accept": "application/json"}
        
        self.__resource_meta = {}
        self.__connection = HTTPSConnection(self.host)
        self.__set_base_url()
        
        
    def meta_data(self):
        """
        Return a string representation of resource-to-url mappings 
        """
        return simplejson.dumps(self.__resource_meta)    
        
        
    def __set_base_url(self):
        """
        Hit the base url and get the urls and resources from 
        the server
        """
        result = self.get("Account")
        log.debug(pformat(result))
        account_id = result["accountID"]
        self.resource_base_url = "%s/%s" % (self.resource_base_url, account_id)
        log.info("Resource Base URL %s" % self.resource_base_url)
        
        
    
    def get(self, url="", query={}, name=None):
        """
        Perform the GET request and return the parsed results
        """
        
        resource = url if not name else name
        qs = urllib.urlencode(query)
        if qs:
            qs = "?%s" % qs
            
        if url in ["Account", "Control"]:
            url = "%s/%s.json%s" % (self.base_url, url, qs)
        else:
            url = "%s/%s.json%s" % (self.resource_base_url, url, qs)
            
        log.debug("GET %s" % (url))
        
        retries = 1
        last_code = 503
        result = {}
        
        while retries < 4 and last_code == 503: 
            self.__connection.connect()
            request = self.__connection.request("GET", url, None, self.__headers)
            response = self.__connection.getresponse()
            data = response.read()
            self.__connection.close()
            
            log.debug("GET %s status %d" % (url,response.status))
            
            last_code = response.status
            
            # Check the return status
            if response.status == 200:
                result = simplejson.loads(data)
                log.debug("attributes %s" % data)
                #if not int(result["@attributes"]["count"]):
                #    raise EmptyResponseWarning("%d %s @ https://%s%s" % (response.status, response.reason, self.host, url))
                
            elif response.status == 204:
                raise EmptyResponseWarning("%d %s @ https://%s%s" % (response.status, response.reason, self.host, url))
            
            elif response.status == 503:
                # Wait a minute
                log.critical("Max API call rate exceeded - waiting 60s [try %d]" % (retries * 20))
                time.sleep(retries * 20)
                retries += 1
            
            elif response.status == 404:
                log.debug("%s returned 404 status" % url)
                raise HTTPException("%d %s @ https://%s%s" % (response.status, response.reason, self.host, url))
            
            elif response.status >= 400:
                _result = simplejson.loads(data)
                log.debug("OUTPUT %s" % _result)
                raise HTTPException("%d %s @ https://%s%s" % (response.status, response.reason, self.host, url))
        
            if not result.has_key(resource):
                raise EmptyResponseWarning("%d %s @ https://%s%s" % (response.status, response.reason, self.host, url))
        return result[resource]
    
    
    
    def get_url(self, resource_name):
        """
        Lookup the "url" for the resource name from the internally stored resource mappings
        """
        return self.__resource_meta.get(resource_name,{}).get("url", None)
    
    def get_resource_url(self, resource_name):
        """
        Lookup the "resource" for the resource name from the internally stored resource mappings
        """
        return self.__resource_meta.get(resource_name,{}).get("resource", None)
        
        
    def update(self, url, updates):
        """
        Make a PUT request to save updates
        """
        url = "%s/%s.json" % (self.resource_base_url, url)
        log.debug("PUT %s" % (url))
        self.__connection.connect()
        
        put_headers = {"Content-Type": "application/json"}
        put_headers.update(self.__headers)
        request = self.__connection.request("PUT", url, simplejson.dumps(updates), put_headers)
        response = self.__connection.getresponse()
        data = response.read()
        self.__connection.close()
        
        log.debug("PUT %s status %d" % (url,response.status))
        log.debug("OUTPUT: %s" % data)
        
        result = {}
        if response.status == 200:
            result = simplejson.loads(data)
        
        elif response.status == 204:
            raise EmptyResponseWarning("%d %s @ https://%s%s" % (response.status, response.reason, self.host, url))
        
        elif response.status == 404:
            log.debug("%s returned 404 status" % url)
            raise HTTPException("%d %s @ https://%s%s" % (response.status, response.reason, self.host, url))
        
        elif response.status >= 400:
            _result = simplejson.loads(data)
            log.debug("OUTPUT %s" % _result)
            raise HTTPException("%d %s @ https://%s%s" % (response.status, response.reason, self.host, url))
        
        return result
    
    def delete(self, url, name=None):
        resource = url if not name else name
        url = "%s/%s.json" % (self.resource_base_url, url)
        log.debug("DELETE %s" % (url))
        self.__connection.connect()
        
        put_headers = {"Content-Type": "application/json"}
        put_headers.update(self.__headers)
        request = self.__connection.request("DELETE", url, None, put_headers)
        response = self.__connection.getresponse()
        data = response.read()
        self.__connection.close()
        
        log.debug("DELETE %s status %d" % (url,response.status))
        log.debug("OUTPUT: %s" % data)
        
        result = {}
        if response.status == 200:
            result = simplejson.loads(data)
        
        elif response.status == 204:
            raise EmptyResponseWarning("%d %s @ https://%s%s" % (response.status, response.reason, self.host, url))
        
        elif response.status == 404:
            log.debug("%s returned 404 status" % url)
            raise HTTPException("%d %s @ https://%s%s" % (response.status, response.reason, self.host, url))
        
        elif response.status >= 400:
            _result = simplejson.loads(data)
            log.debug("OUTPUT %s" % _result)
            raise HTTPException("%d %s @ https://%s%s" % (response.status, response.reason, self.host, url))
        
        return result
    
        
    
    def create(self, url, properties, name=""):
        resource = url if not name else name
        url = "%s/%s.json" % (self.resource_base_url, url)
        log.debug("POST %s" % (url))
        log.debug("Creating %s" % pformat(properties))
        self.__connection.connect()
        
        put_headers = {"Content-Type": "application/json"}
        put_headers.update(self.__headers)
        request = self.__connection.request("POST", url, simplejson.dumps(properties), put_headers)
        response = self.__connection.getresponse()
        data = response.read()
        self.__connection.close()
        
        log.debug("POST %s status %d" % (url,response.status))
        log.debug("OUTPUT: %s" % data)
        
        result = {}
        if response.status == 200:
            result = simplejson.loads(data)
        
        elif response.status == 204:
            raise EmptyResponseWarning("%d %s @ https://%s%s" % (response.status, response.reason, self.host, url))
        
        elif response.status == 404:
            log.debug("%s returned 404 status" % url)
            raise HTTPException("%d %s @ https://%s%s" % (response.status, response.reason, self.host, url))
        
        elif response.status >= 400:
            _result = simplejson.loads(data)
            log.debug("OUTPUT %s" % _result)
            raise HTTPException("%d %s @ https://%s%s" % (response.status, response.reason, self.host, url))
        
        return result[resource]
    
    
    def __repr__(self):
        return "Connection %s" % (self.host)
    
    


    