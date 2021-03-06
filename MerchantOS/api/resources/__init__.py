import sys
import logging
from pprint import pprint
from MerchantOS.api.lib.mapping import Mapping
from MerchantOS.api.lib.filters import FilterSet
from MerchantOS.api.lib.connection import EmptyResponseWarning

log = logging.getLogger("MerchantOS")


class ResourceAccessor(object):
    """
    Provides methods that will create, get, and enumerate resourcesObjects.
    """
    
    def __init__(self, resource_name, connection):
        """
        Constructor
        
        @param resource_name: The name of the resource being accessed.  There must be a
                              corresponding ResourceObject class
        @type resource_name: String
        @param connection: Connection to the bigCommerce REST API
        @type connection: {Connection}
        """
        log.debug("Resource Accessor for %s" % resource_name)
        self._parent = None
        self.__resource_name = resource_name
        self._connection = connection
        
        try:
            mod = __import__('%s' % resource_name, globals(), locals(), [resource_name], -1)
            self._klass = getattr(mod, resource_name)
        except:
            self._klass = ResourceObject
            
        # Work around for option values URL being incorrect
        self._url = self.__resource_name
            
         
    def __get_page(self, offset, limit, query={}):
        """
        Get specific pages
        """
        log.debug("Getting Page")
        _query = {"offset": offset, "limit": limit}
        
        _query.update(query)
        result =  self._connection.get(self._url, _query)
        return [result] if isinstance(result, dict) else result
    
    
    def enumerate(self, start=0, limit=0, query={}, max_per_call=100):
        """
        Enumerate resources
        
        @param start: The instance to start on
        @type pages: int
        @param limit: The number of items to return, Set to 0 to return all items
        @type start_page: int
        @param query: Search criteria
        @type query: FilterSet
        @param max_per_call: Number of items to return per request
        @type max_per_call: int
        """
        _query = {}
        if query:
            _query = query
        
            
        requested_items = limit if limit else sys.maxint
        max_per_call = min(max_per_call, 100)
        max_per_call = min(requested_items, max_per_call)
        
        offset = start
         
        #while current_page < total_pages and requested_items:
        while requested_items:
            try:
                for res in self.__get_page(offset, max_per_call, _query):
                    requested_items -= 1
                    yield self._klass(self._connection, self._url, res, self._parent)
                
                offset = offset + max_per_call
                
                
            # If the response was empty - we are done
            except EmptyResponseWarning:
                requested_items = 0
            except:
                raise
                    


    def get(self, id, query={}):
        url = "%s/%s" % (self._url, id)
        try:
            result = self._connection.get(url, query, name=self.__resource_name)
            return self._klass(self._connection, self._url, result, self._parent)
        except:
            return None
    
    
    def create(self, properties, opts={}):
        try:
            result = self._connection.create(self._url, properties, name=self.__resource_name)
            print result
            return self._klass(self._connection, self._url, result, self._parent)
        except:
            return None
        pass
    
    def get_count(self, query={}):
        
        if query:
            _query = query.query_dict()
        else:
            _query = query
        result = self._connection.get("%s/%s" % (self._url, "count"), _query)
        return result.get("count")
    
    def filters(self):
        try:
            return self._klass.filter_set()
        except:
            return FilterSet()
    
    def get_name(self):
        return self.__resource_name
    
    
    def get_subresources(self):
        return self._klass.sub_resources
    
    name = property(fget=get_name)
    
    
class SubResourceAccessor(ResourceAccessor):
    
    def __init__(self, klass, url, connection, parent):
        """
        """
        self._parent = parent
        self._connection = connection
        self._klass = klass
        self._url = url if isinstance(url, basestring) else url["resource"]
        
    

class ResourceObject(object):
    """
    The realized resource instance type.
    """
    writeable = [] # list of properties that are writeable
    read_only = [] # list of properties that are read_only
    sub_resources = {}  # list of properties that are subresources
    can_create = False  # If create is supported
    can_update = False
    
    def __init__(self, connection, url, fields, parent):
        #  Very important!! These two lines must be first to support 
        # customized getattr and setattr
        self._fields = fields or dict()
        self._updates = {} # the fields to update
        
        self._parent = parent
        self._connection = connection
        
        _name = "%s%s" % (url[0].lower(), url[1:])
        self._url = "%s/%s" % (url, self._fields["%sID" % _name])
        log.debug("Resource Object URL: %s" % self._url)
        
        
    def __getattr__(self, attrname):
        """
        Override get access to look up values in the updates first, 
        then from the fields, if the fields value indicates that
        its a sub resource that is not yet realized, make the call to
        inflate the subresource object.
        """
        
        # If the value was set, when asked give this value,
        # not the original value
        if self._updates.has_key(attrname):
            return self._updates[attrname]
        
        if not self._fields.has_key(attrname):
            raise AttributeError("%s not available" % attrname)
        # Look up the value in the _fields
        data = self._fields.get(attrname,None)
        
        if data is None:
            return data
        else:
            
            # if we are dealing with a sub resource and we have not 
            # already made the call to inflate it - do so
            if self.sub_resources.has_key(attrname) and isinstance(data, dict):
                
                _con = SubResourceAccessor(self.sub_resources[attrname].get("klass", ResourceObject), 
                                           data, self._connection, 
                                           self)
                
                # If the subresource is a list of objects
                if not self.sub_resources[attrname].get("single", False):
                    _list = []
                    for sub_res in _con.enumerate():
                        _list.append(sub_res)
                    self._fields[attrname] = _list
                
                # if the subresource is a single object    
                else:
                    self._fields[attrname] = _con.get("")
                    
            # Cast all dicts to Mappings - for . access
            elif isinstance(data, dict):
                val = Mapping(data)
                self._fields[attrname] = val
                
            return self._fields[attrname]
            
        raise AttributeError
    
    
    def __setattr__(self, name, value):
        """
        All sets on field properties are caches in the updates dictionary
        until saved
        """
        if name == "_fields":
            object.__setattr__(self, name, value)
        
        elif self._fields.has_key(name):
            if name in self.read_only:
                raise AttributeError("Attempt to assign to a read-only property '%s'" % name)
            elif not self.writeable or name in self.writeable:
                self._updates.update({name:value})
        else:
            object.__setattr__(self, name, value)
            
        
    def get_url(self):
        return self._url
    
    def save(self):
        """
        Save any updates and set the fields to the values received 
        from the return value and clear the updates dictionary
        """
        if self._updates:
            log.info("Updating %s" % self.get_url())
            log.debug("Data: %s" % self._updates)
            
            results = self._connection.update(self.get_url(), self._updates)
            self._updates.clear()
            self._fields = results
    
    def delete(self):
        return self._connection.delete(self.get_url(), )            
        
    def __repr__(self):
        return str(self._fields)
    
    def to_dict(self):
        return self._fields
    

