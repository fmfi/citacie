# -*- coding: utf-8 -*-
from suds.client import Client
from model import Publication, Author, Identifier
import time

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
  
  def _retrieve_by_id(self, uid):
    params = self.search.factory.create('retrieveParameters')
    params.firstRecord = 1
    params.count = 2
    return self.search.service.retrieveById(databaseId='WOK', uid=uid,
      queryLanguage='en', retrieveParameters=params)
  
  def _convert_to_publication(self, record):
    def extract_label(group, label):
      for pair in group:
        if pair.label == label:
          return pair.value      
      return None
    
    def extract_single(group, label):
      l = extract_label(group, label)
      if l == None:
        return None
      if len(l) == 0:
        return None
      if len(l) > 1:
        raise ValueError('Expecting single value only')
      return unicode(l[0])
    
    def parse_author(fullname):
      parts = fullname.split(',', 1)
      if len(parts) > 1:
        names = parts[1].split()
      else:
        names = None
      return Author(parts[0], names)
    
    title = u''.join(extract_label(record.title, 'Title'))
    authors = extract_label(record.authors, 'Authors')
    parsed_authors = [parse_author(unicode(x)) for x in authors]
    year = extract_single(record.source, 'Published.BiblioYear')
    p = Publication(title, parsed_authors, year)
    
    p.published_in = extract_single(record.source, 'SourceTitle')
    p.pages = extract_single(record.source, 'Pages')
    p.volume = extract_single(record.source, 'Volume')
    p.series = extract_single(record.source, 'BookSeriesTitle')
    p.issue = extract_single(record.source, 'Issue')
    p.special_issue = extract_single(record.source, 'SpecialIssue')
    p.supplement = extract_single(record.source, 'Supplement')
    
    wokid = Identifier(unicode(record.uid), type='WOK', description='Web Of Knowledge')
    p.identifiers.append(wokid)
    
    idtypes = {'Identifier.Isbn': 'ISBN',
               'Identifier.Issn': 'ISSN',
               'Identifier.Doi': 'DOI',
              }
    
    for pair in record.other:
      if not pair.label in idtypes:
        continue
      for value in pair.value:
        p.identifiers.append(Identifier(unicode(value), type=idtypes[pair.label]))
    
    return p
  
  def _convert_list(self, records):
    return [self._convert_to_publication(x) for x in records]
  
  def retrieve_by_id(self, uid):
    result = self._retrieve_by_id(uid)
    if result.recordsFound != 1:
      return None
    return self._convert_to_publication(result.records[0])
  
  def _search(self, query, database_id='WOS', timespan=None):
    query_params = self.search.factory.create('queryParameters')
    query_params.databaseId = database_id
    query_params.userQuery = query
    query_params.queryLanguage = 'en'
    
    if timespan != None:
      ts = self.search.factory.create('timeSpan')
      ts.begin = timespan[0]
      ts.end = timespan[1]
      query_params.timeSpan = ts
    
    retr_params = self.search.factory.create('retrieveParameters')
    retr_params.firstRecord = 1
    retr_params.count = 100
    first_result = self.search.service.search(query_params, retr_params)
    
    records = []
    pages = first_result.recordsFound / retr_params.count
    if first_result.recordsFound % retr_params.count > 0:
      pages += 1
    
    records.extend(first_result.records)
        
    # retrieve additional records
    for pagenum in range(1, pages):
      retr_params.firstRecord += retr_params.count
      time.sleep(1) # throttle
      additional_result = self.search.service.retrieve(first_result.queryId, retr_params)
      records.extend(additional_result.records)
    
    if len(records) < first_result.recordsFound:
      raise ValueError('Failed retrieving all results')
    
    return records
  
  def search_by_author(self, surname, name=None, year=None):
    # TODO escaping
    query = u'AU=('
    query += surname
    if name is not None:
      query += u' ' + name
    query += u')'
    if year is not None:
      query += ' AND PY={}'.format(year)
    return self._convert_list(self._search(query))
    
  def close(self):
    self.auth.service.closeSession()
  
  def __enter__(self):
    self.open()
    return self
  
  def __exit__(self, type, value, traceback):
    self.close()
    return False

if __name__ == '__main__':
  import argparse
  
  def print_results(args, wok, results):
    if args.repr:
      print '['
    for result in results:
      display_raw = args.raw
      pub = None
      try:
        pub = wok._convert_to_publication(result)
      except:
        print 'Failed to convert record:'
        display_raw = True
      if pub:
        if args.repr:
          print pub.repr(pretty=True) + ','
        else:
          print pub
      if display_raw:
        print result
    if args.repr:
      print ']'
  
  def search(args, wok):
    print_results(args, wok, wok._search(args.query))
  
  def retrieve(args, wok):
    print_results(args, wok, wok._retrieve_by_id(args.id).records)
  
  def services(args, wok):
    print wok.auth
    print '-'*80
    print wok.search
  
  parser = argparse.ArgumentParser()
  parser.add_argument('--raw', action='store_true', help='show raw results always')
  parser.add_argument('--repr', action='store_true', help='show python code instead of formatted result')
  
  subparsers = parser.add_subparsers()
  
  parser_search = subparsers.add_parser('search')
  parser_search.add_argument('query')
  parser_search.set_defaults(func=search)
  
  parser_retrieve = subparsers.add_parser('retrieve')
  parser_retrieve.add_argument('id')
  parser_retrieve.set_defaults(func=retrieve)
  
  parser_services = subparsers.add_parser('services')
  parser_services.set_defaults(func=services)
  
  args = parser.parse_args()
  
  with WOK() as wok:
    args.func(args, wok)