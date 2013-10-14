#!/usr/bin/env python
from suds.client import Client

class WOK:
  def __init__(self):
    self.wsdl_auth = 'http://search.webofknowledge.com/esti/wokmws/ws/WOKMWSAuthenticate?wsdl'
    self.wsdl_search = 'http://search.webofknowledge.com/esti/wokmws/ws/WokSearchLite?wsdl'
    self.auth = None
    self.search = None
    self.session_id = None
  
  def open(self):
    self.auth = Client(self.wsdl_auth)
    self.session_id = self.auth.service.authenticate()
    self.search = Client(self.wsdl_search, headers={'Cookie': 'SID=' + self.session_id})
  
  def _retrieveById(self, uid):
    params = self.search.factory.create('retrieveParameters')
    params.firstRecord = 1
    params.count = 2
    return self.search.service.retrieveById(databaseId='WOK', uid=uid,
      queryLanguage='en', retrieveParameters=params)
    
  def close(self):
    self.auth.service.closeSession()
  
  def __enter__(self):
    self.open()
    return self
  
  def __exit__(self, type, value, traceback):
    self.close()
    return False

if __name__ == '__main__':
  with WOK() as wok:
    print wok._retrieveById('WOS:000308512600015')