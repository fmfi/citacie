# -*- coding: utf-8 -*-
from suds.client import Client
from model import Publication, Author, Identifier, URL
import time
from xmlbuilder import XMLBuilder
import types
import urllib2
from contextlib import closing
from defusedxml import ElementTree

class WOK:
  def __init__(self):
    self.wsdl_auth = 'http://search.webofknowledge.com/esti/wokmws/ws/WOKMWSAuthenticate?wsdl'
    self.wsdl_search = 'http://search.webofknowledge.com/esti/wokmws/ws/WokSearchLite?wsdl'
    self.auth = None
    self.search = None
    self.session_id = None
    self.lamr = LAMR()
  
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
  
  def _retrieve_links(self, publications):
    pubs_by_uids = {}
    for pub in publications:
      for id in Identifier.find_by_type(pub.identifiers, 'WOK'):
        pubs_by_uids[id.value] = pub
    uids = pubs_by_uids.keys()
    result_by_uids = self.lamr.retrieve_by_ids(uids)
    for uid, result in result_by_uids.iteritems():
      pub = pubs_by_uids[uid]
      if 'timesCited' in result:
        # TODO
        pass
      if 'sourceURL' in result:
        pub.source_urls.append(URL(result['sourceURL'], type='WOK', description=u'View record in Web of Science®'))
      if 'citingArticlesURL' in result:
        pub.cite_urls.append(URL(result['citingArticlesURL'], type='WOK', description=u'View citing articles in Web of Science®'))
      if 'message' in result:
        pub.errors.append(u'Failed loading article URLs: ' + unicode(result['message']))
  
  def search_by_author(self, surname, name=None, year=None):
    # TODO escaping
    query = u'AU=('
    query += surname
    if name is not None:
      query += u' ' + name
    query += u')'
    if year is not None:
      query += ' AND PY={}'.format(year)
    publications =  self._convert_list(self._search(query))
    self._retrieve_links(publications)
    return publications
    
  def close(self):
    self.auth.service.closeSession()
  
  def __enter__(self):
    self.open()
    return self
  
  def __exit__(self, type, value, traceback):
    self.close()
    return False

class LAMR:
  def __init__(self):
    self.post_url = 'https://ws.isiknowledge.com/cps/xrpc'
  
  def _build_retrieve_request(self, fields, uids):
    x = XMLBuilder('request', xmlns='http://www.isinet.com/xrpc42')
    with x.fn(name='LinksAMR.retrieve'):
      with x.list:
        x.map
        with x.map:
          with x.list(name='WOS'):
            for field in fields:
              x.val(field)
        with x.map:
          for i, uid in enumerate(uids):
            with x.map(name='cite{}'.format(i)):
              x.val(uid, name='ut')
    return str(x)
  
  def _parse_retrieve_response(self, response):
    et = ElementTree.fromstring(response)
    fn = et.find('{http://www.isinet.com/xrpc42}fn')
    if fn.get('rc') != 'OK':
      raise ValueError('Did not receive OK reply for LAMR response')
    m = fn.find('{http://www.isinet.com/xrpc42}map')
    results = {}
    for cite in m:
      name = cite.get('name')
      vals = {}
      wos = cite.find('{http://www.isinet.com/xrpc42}map')
      for val in wos:
        vals[val.get('name')] = val.text
      results[name] = vals
    return results
  
  def _retrieve(self, fields, uids):
    req_body = self._build_retrieve_request(fields, uids)
    with closing(urllib2.urlopen(self.post_url, req_body)) as f:
      response = f.read()
    parsed_response = self._parse_retrieve_response(response)
    response_by_uid = {}
    for i, uid in enumerate(uids):
      key = 'cite{}'.format(i)
      if key not in parsed_response:
        continue
      response_by_uid[uid] = parsed_response[key]
    return response_by_uid

  def retrieve_by_ids(self, uids):
    # split into requests of max 50
    pagesize = 50
    pages = len(uids) / pagesize
    if len(uids) % pagesize > 0:
      pages += 1
    results = {}
    for page in range(pages):
      sublist = uids[page * pagesize:min((page + 1) * pagesize, len(uids))]
      results.update(self._retrieve(['timesCited', 'sourceURL', 'citingArticlesURL'], sublist))
    return results

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
  
  def search(args):
    with WOK() as wok:
      print_results(args, wok, wok._search(args.query))
  
  def retrieve(args):
    with WOK() as wok:
      print_results(args, wok, wok._retrieve_by_id(args.id).records)
  
  def search_by_author(args):
    with WOK() as wok:
      for pub in wok.search_by_author(args.surname, name=args.name, year=args.year):
        print pub
  
  def services(args):
    with WOK() as wok:
      print wok.auth
      print '-'*80
      print wok.search
  
  def lamr_retrieve(args):
    lamr = LAMR()
    for uid, vals in lamr.retrieve_by_ids(args.uid).iteritems():
      print uid
      for valname, val in vals.iteritems():
        print '  {}: {}'.format(valname, val)
  
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
  
  parser_author = subparsers.add_parser('search_by_author')
  parser_author.add_argument('surname')
  parser_author.add_argument('--name')
  parser_author.add_argument('--year')
  parser_author.set_defaults(func=search_by_author)
  
  parser_services = subparsers.add_parser('services')
  parser_services.set_defaults(func=services)
  
  parser_retrieve = subparsers.add_parser('lamr_retrieve')
  parser_retrieve.add_argument('uid', nargs='+')
  parser_retrieve.set_defaults(func=lamr_retrieve)
  
  args = parser.parse_args()
  
  args.func(args)
