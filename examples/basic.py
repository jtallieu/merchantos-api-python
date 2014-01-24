STORE_HOST = "api.merchantos.com"
STORE_TOKEN = "12nahnay345"
STORE_TOKEN = "apikey"


#STORE_USERID = "joey@nahnay.com"

from settings import *
import sys
sys.path.append("..")

import logging
from pprint import pprint
from MerchantOS.api import ApiClient
from datetime import datetime, timedelta

logging.basicConfig(level=logging.DEBUG, 
                    stream=sys.stdout,
                    format='%(asctime)s %(levelname)-8s[%(name)s] %(message)s',
                    datefmt='%m/%d %H:%M:%S')
log = logging.getLogger("main")
pos_log = logging.getLogger("pos")




def get_product(api, id):
    q = {"load_relations":"all"}
    prod = {}
    try:
        product = api.Item.get(id, query=q)
        pprint(product.to_dict())
        prod["name"] = product.description
        prod["sku"] = product.upc
        prod["id"] = product.itemID
        quantity = 0
        for inv in product.ItemShops["ItemShop"]:
            if inv["shopID"] == '0':
                quantity = int(inv["qoh"])
                break 
        prod["quantity"] = quantity
        return prod
    except:
        pos_log.exception("Unable to get product %s" % id)
        
    return None
        



def get_updated_products(api, since):
    
    prods = {}
    sinceStr = since.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    q = {"timeStamp": ">=,%s" % sinceStr}
    
    pos_log.info("Gathering products modified since %s" % since)
    
    pos_log.info("Checking for checked-in items")
    q1 = {"timeStamp": ">=,%s" % sinceStr,
          "checkedIn": ">,0"}
    q2 = {"createTime": ">=,%s" % sinceStr}
    
    for line in api.OrderLine.enumerate(query=q1):
        id = line.itemID
        if not prods.has_key(id):
            prods[id] = {"counted": False, "sold": False, "updated": False, "received": False}
        prods[id]["received"] = True
    
    pos_log.info("Checking for inventory counts")   
    
    for line in api.InventoryCountReconcile.enumerate(query=q2):
        id = line.itemID
        if not prods.has_key(id):
            prods[id] = {"counted": False, "sold": False, "updated": False, "received": False}
        prods[id]["counted"] = True
     
    pos_log.info("Checking for Sales")
    for line in api.SaleLine.enumerate(query=q2):
        id = line.itemID
        if not prods.has_key(id):
            prods[id] = {"counted": False, "sold": False, "updated": False, "received": False}
        prods[id]["sold"] = True
    
    q3 = {"timeStamp": ">=,%s" % sinceStr,
          "load_relations":"all"}
    pos_log.info("Checking for Product Updates")
    for line in api.Item.enumerate(query=q3):
        id = line.itemID
        if not prods.has_key(id):
            prods[id] = {"counted": False, "sold": False, "updated": False, "received": False}
        prods[id]["updated"] = True
    return prods 
    
def get_products(api, since):
        #api = self.driver
        q = {"load_relations":"all"}
        if since:
            sinceStr = since.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            q.update({"timeStamp": ">=,%s" % sinceStr})
        
        
        for product in api.Item.enumerate(query=q):
            prod = {}
            prod["name"] = product.description
            prod["sku"] = product.upc
            prod["id"] = product.itemID
            prod["quantity"] = 0
            
            #pprint (product.ItemShops["ItemShop"])
            
            if isinstance(product.ItemShops["ItemShop"], dict):
                prod["quantity"] = int(product.ItemShops["ItemShop"]["qoh"])
                
            elif isinstance(product.ItemShops["ItemShop"], list):
                for inv in product.ItemShops["ItemShop"]:
                    if inv["shopID"] == '0':
                        prod["quantity"] = int(inv["qoh"])
                        break
                    else:
                        prod["quantity"] += int(inv["qoh"])
                         
            yield(prod)
        
    
if __name__ == "__main__":
    log.debug("HOST %s, USER: %s" % (STORE_HOST, STORE_USERID))
    api = ApiClient(STORE_HOST, STORE_TOKEN, STORE_USERID)
    
    
    q = {"timeStamp": ">=,2012-12-19T16:01:15+00:00"}
    
    dt = datetime.utcnow() - timedelta(hours=3)
    
    items = get_updated_products(api, datetime(2013, 8,27,0,0,0))
    pprint (items)
    
    """
    for shop in api.Shop.enumerate():
        print shop
    """
    """
    items = get_updated_products(api, None)
    pprint (items)
    
    for k in items.keys():
        print k
        pro = get_product(api, k)
        print pro
    """
    
    #product = get_product(api, "56936")
    #pprint (product)
    """
    for p in get_products(api, None):
        pprint(p)
    """
     
    """
    for prod in api.InventoryCountItem.enumerate():
        print prod
        
    
    
    for ord in api.Order.enumerate(query={"load_relations":"all"}):
        print ord
    
    
    

    for ord in api.Order.enumerate():
        print ord
        for line in api.OrderLine.enumerate(query={"orderID":ord.orderID}):
            print line
            
    """