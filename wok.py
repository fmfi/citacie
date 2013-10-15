# -*- coding: utf-8 -*-
from suds.client import Client
from model import Publication, Author, Identifier

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
  
  def _convertToPublication(self, record):
    def extract_label(group, label):
      for pair in group:
        if pair.label == label:
          return pair.value      
      return None
    
    def extract_single(group, label):
      l = extract_label(group, label)
      if l == None:
        return None
      if len(l) != 1:
        raise ValueError('Expecting single value only')
      return l[0]
    
    def parse_author(fullname):
      parts = fullname.split(',', 1)
      if len(parts) > 1:
        names = parts[1].split()
      else:
        names = None
      return Author(parts[0], names)
    
    title = u''.join(extract_label(record.title, 'Title'))
    authors = extract_label(record.authors, 'Authors')
    parsed_authors = [parse_author(x) for x in authors]
    year = extract_single(record.source, 'Published.BiblioYear')
    p = Publication(title, parsed_authors, year)
    
    p.published_in = extract_single(record.source, 'SourceTitle')
    p.pages = extract_single(record.source, 'Pages')
    p.volume = extract_single(record.source, 'Volume')
    p.series = extract_single(record.source, 'BookSeriesTitle')
    
    wokid = Identifier(record.uid, type='WOK', description='Web Of Knowledge')
    p.identifiers.append(wokid)
    
    for pair in record.other:
      if pair.label == 'Identifier.Isbn':
        for isbn in pair.value:
          p.identifiers.append(Identifier(isbn, type='ISBN'))
      elif pair.label == 'Identifier.Issn':
        for issn in pair.value:
          p.identifiers.append(Identifier(issn, type='ISSN'))
    
    return p
    
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
    result = wok._retrieveById('WOS:000308512600015')
    print result
    for record in result.records:
      publication = wok._convertToPublication(record)
      print publication