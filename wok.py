# -*- coding: utf-8 -*-
from suds.client import Client
from model import Publication, Author, Identifier, URL, Index
import time
from xmlbuilder import XMLBuilder
import types
import urllib2
from contextlib import closing
from defusedxml import ElementTree
from data_source import DataSource, DataSourceConnection
import html5lib
import lxml.etree
import re
from collections import OrderedDict, namedtuple
from urllib import urlencode, quote
import requests
from util import make_page_range

Page = namedtuple('Page', ('page', 'start_index', 'end_index', 'count'))

def pages(item_count, page_size, start_page=1, start_index=1, end_inclusive=False):
  page_count = item_count / page_size
  if item_count % page_size > 0:
      page_count += 1
  for page_index in range(page_count):
    page_start_index = start_index + page_index * page_size
    page_end_index = min(page_start_index + page_size, start_index + item_count)
    page_item_count = page_end_index - page_start_index
    if end_inclusive:
      page_end_index -= 1
    yield Page(start_page + page_index, page_start_index, page_end_index, page_item_count)

class WokWS(DataSource):
  def __init__(self, lamr=None):
    self.lamr = lamr
  
  def connect(self):
    return WokWSConnection(lamr=self.lamr)

class WokWSConnection(DataSourceConnection):
  def __init__(self, lamr=None):
    self.wsdl_auth = 'http://search.webofknowledge.com/esti/wokmws/ws/WOKMWSAuthenticate?wsdl'
    self.wsdl_search = 'http://search.webofknowledge.com/esti/wokmws/ws/WokSearchLite?wsdl'
    self.lamr = lamr
    
    self.auth = Client(self.wsdl_auth)
    self.session_id = self.auth.service.authenticate()
    self.search = Client(self.wsdl_search, headers={'Cookie': 'SID=' + self.session_id})    
  
  def close(self):
    self.auth.service.closeSession()
  
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
    
    title = u''.join(extract_label(record.title, 'Title'))
    authors = extract_label(record.authors, 'Authors')
    parsed_authors = [Author.parse_sn_first(unicode(x)) for x in authors]
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
  
  def _search(self, query, database_id='WOS', timespan=None, edition=None):
    query_params = self.search.factory.create('queryParameters')
    query_params.databaseId = database_id
    query_params.userQuery = query
    query_params.queryLanguage = 'en'
    
    if edition:
      ed = self.search.factory.create('editionDesc')
      ed.collection = database_id
      ed.edition = edition
      query_params.editions = [ed]
    
    if timespan != None:
      ts = self.search.factory.create('timeSpan')
      ts.begin = timespan[0]
      ts.end = timespan[1]
      query_params.timeSpan = ts
    
    retr_params = self.search.factory.create('retrieveParameters')
    retr_params.firstRecord = 1
    retr_params.count = 100
    time.sleep(1) # throttle
    first_result = self.search.service.search(query_params, retr_params)
    
    if first_result.recordsFound == 0:
      return []
    
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
  
  def search_citations(self, publications):
    raise NotImplemented # sluzba nepodporuje
  
  def _find_editions(self, uts):
    try_editions = ['SCI', 'SSCI', 'AHCI', 'ISTP', 'ISSHP', 'BSCI', 'BHCI']
    
    unknown = set(uts)
    utmap = {}
    
    for edition in try_editions:
      if len(unknown) == 0:
        break
      query = u'UT=({})'.format(u' OR '.join(ut for ut in unknown))
      print query
      for record in self._search(query, edition=edition):
        record_uid = unicode(record.uid)
        utmap[record_uid] = edition
        unknown.remove(record_uid)
    
    return utmap
  
  def assign_indexes(self, publications):
    pub_by_id = {}
    
    for pub in publications:
      e = list(Index.find_by_type(pub.indexes, 'WOS'))
      if len(e) > 0:
        continue
    
      ut = list(Identifier.find_by_type(pub.identifiers, 'WOK'))
      if len(ut) == 0:
        continue
      ut = ut[0].value
      
      pub_by_id[ut] = pub
    
    editions = self._find_editions(pub_by_id.keys())
    print repr(editions)
    for ut, edition in editions.iteritems():
      print ut, edition
      pub_by_id[ut].indexes.append(Index(edition, type='WOS'))

class LAMR:
  def __init__(self, delay=1.0):
    self.post_url = 'https://ws.isiknowledge.com/cps/xrpc'
    self.delay = delay
  
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
    if self.delay:
      time.sleep(self.delay)
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

class WokWeb(DataSource):
  def __init__(self, additional_headers=None):
    self.url = 'http://apps.webofknowledge.com/'
    #self.url = 'http://localhost:8000/'
    if additional_headers == None:
      additional_headers = {'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0'}
    self.additional_headers = additional_headers
    
  def connect(self):
    return WokWebConnection(self.url, additional_headers=self.additional_headers)
  
class WokWebConnection(DataSourceConnection):
  def __init__(self, url, additional_headers=None):
    self.url = url
    self.additional_headers = additional_headers
    self.session = requests.Session()
    if additional_headers:
      self.session.headers.update(additional_headers)
  
  def _delay(self):
    time.sleep(1)
  
  def _strip(self, e):
    prev =  e.getprevious()
    par = e.getparent()
    text = e.text + e.tail
    if prev is not None:
      if prev.tail is not None:
        prev.tail += text
      else:
        prev.tail = text
    else:
      if par.text is not None:
        par.text += text
      else:
        par.text = text
    par.remove(e)
  
  def _parse_list_for_author(self, response, encoding=None):
    et = html5lib.parse(response, encoding=encoding, treebuilder="lxml")
    pubs = []
    result_count = int(et.find("//*[@id='hitCount.bottom']").text.strip())
    for td in et.findall(".//{http://www.w3.org/1999/xhtml}div[@class='records_chunk']//{http://www.w3.org/1999/xhtml}td[@class='summary_data']"):
      # remove highlight spans for easier parsing
      for el in td.findall(".//*[@class='hitHilite']"):
        self._strip(el)
      
      labels = td.findall(".//{http://www.w3.org/1999/xhtml}span[@class='label']")
      data = {}
      for label in labels:
        name = label.text.strip().rstrip(':')
        if name == 'Title':
          value = label.getnext().find("./{http://www.w3.org/1999/xhtml}value").text
          data['href'] = label.getnext().attrib['href']
        else:
          sibling = label.getnext()
          if sibling == None or sibling.attrib.get('class') == 'label':
            value = label.tail
          else:
            value = sibling.text
            if name == 'Times Cited' and 'href' in sibling.attrib:
              data['cited_href'] = sibling.attrib['href']
        value = value.strip()
        data[name] = value
      year = re.search(r'(19|20)\d\d', data['Published']).group(0)
      data['Year'] = year
      pubs.append(data)
    return result_count, pubs
      
  def _list_to_publications(self, l):
    pubs = []
    for data in l:
      authors = []
      authors_incomplete = False
      if 'Author(s)' in data:
        for author_text in (unicode(x) for x in data['Author(s)'].split(';')):
          if author_text.strip() == u'et al.':
            authors_incomplete = True
          else:
            authors.append(Author.parse_sn_first(author_text.strip()))
      else:
        authors_incomplete = True
      
      pub = Publication(unicode(data['Title']), authors, int(data['Year']))
      if 'Source' in data:
        pub.published_in = unicode(data['Source'])
      if 'Book Series' in data:
        pub.series = unicode(data['Book Series'])
      if 'Volume' in data:
        pub.volume = unicode(data['Volume'])
      if 'Pages' in data:
        pub.pages = unicode(data['Pages'])
      if 'Issue' in data:
        pub.issue = unicode(data['Issue'])
      if 'Special Issue' in data:
        pub.special_issue = unicode(data['Special Issue'])
      if 'Supplement' in data:
        pub.supplement = unicode(data['Supplement'])
      pub.authors_incomplete = authors_incomplete
      pubs.append(pub)
    return pubs
  
  def search_by_author(self, surname, name=None, year=None):
    raise NotImplemented #TODO use requests instead of mechanize
    with open('response.txt') as f:
      response = f.read()
    count, l = self._parse_list_for_author(response, encoding='utf-8')
    return self._list_to_publications(l)
    self.browser.open(self.url)
    self.browser.select_form('UA_GeneralSearch_input_form')
    self.browser['rs_rec_per_page'] = ['50']
    if year != None:
      self.browser['value(input1)'] = str(year)
      self.browser['value(select1)'] = ['PY']
    fname = surname
    if name:
      fname += ' {}*'.format(name)
    self.browser['value(input2)'] = str(fname)
    self._delay()
    r = self.browser.submit()
    print r.get_data()
    
    #self.browser.select_form('UA_GeneralSearch_input_form')
  
  def _parse_citations_list(self, response, encoding=None):
    et = html5lib.parse(response, encoding=encoding, treebuilder="lxml")
    result_count = int(et.find("//*[@id='hitCount.bottom']").text.strip())
    return result_count
  
  def _get_sid(self):
    return self.session.cookies['SID'].strip('"')
  
  def _get_citations_from_url(self, cite_url, origin_ut):
    r = self.session.get(cite_url)
    count = self._parse_citations_list(r.text)
    
    if count == 0:
      return
    
    for page in pages(count, 500, end_inclusive=True):
      mark_from = str(page.start_index)
      mark_to = str(page.end_index)
      qid = re.search(r'qid=(\d+)', r.text).group(1)
      
      headers = {'Referer': r.url}
      
      data = OrderedDict()
      data['selectedIds'] = ''
      data['viewType'] = 'summary'
      data['product'] = 'WOS'
      data['rurl'] = quote('http://apps.webofknowledge.com/summary.do?SID={sid}&SID={sid}&product=WOS&product=WOS&UT={ut}&qid=6&search_mode=CitingArticles&mode=CitingArticles'.format(sid=quote(self._get_sid(), ''), ut=quote(origin_ut, '')), '')
      data['mark_id'] = 'WOS'
      data['colName'] = 'WOS'
      data['search_mode'] = 'CitingArticles'
      data['locale'] = 'en_US'
      data['view_name'] = 'WOS-CitingArticles-summary'
      data['sortBy'] = 'PY.D;LD.D;SO.A;VL.D;PG.A;AU.A'
      data['mode'] = 'OpenOutputService'
      data['qid'] = qid
      data['SID'] = self._get_sid()
      data['format'] = 'saveToFile'
      data['filters'] = 'USAGEIND AUTHORSIDENTIFIERS ACCESSION_NUM FUNDING SUBJECT_CATEGORY JCR_CATEGORY LANG IDS PAGEC SABBR CITREFC ISSN PUBINFO KEYWORDS CITTIMES ADDRS CONFERENCE_SPONSORS DOCTYPE ABSTRACT CONFERENCE_INFO SOURCE TITLE AUTHORS  '
      data['mark_to'] = mark_to
      data['mark_from'] = mark_from
      data['count_new_items_marked'] = '0'
      data['value(record_select_type)'] = 'range'
      data['markFrom'] = mark_from
      data['markTo'] = mark_to
      data['fields_selection'] = 'USAGEIND AUTHORSIDENTIFIERS ACCESSION_NUM FUNDING SUBJECT_CATEGORY JCR_CATEGORY LANG IDS PAGEC SABBR CITREFC ISSN PUBINFO KEYWORDS CITTIMES ADDRS CONFERENCE_SPONSORS DOCTYPE ABSTRACT CONFERENCE_INFO SOURCE TITLE AUTHORS  '
      data['save_options'] = 'tabMacUTF8'
      
      self._delay()
      
      r2 = self.session.post('http://apps.webofknowledge.com/OutboundService.do?action=go&&', data=data, headers=headers)
      
      for pub in self._parse_tab_delimited(r2.text):
        yield pub
  
  def _parse_tab_delimited(self, text):
    lines = text.splitlines()
    columns = lines[0].split('\t')
    try:
      col_authors = columns.index('AF')
    except ValueError:
      col_authors = columns.index('AU')
    col_title = columns.index('TI')
    col_source = columns.index('SO')
    col_year = columns.index('PY')
    col_issn = columns.index('SN')
    col_isbn = columns.index('BN')
    col_doi = columns.index('DI')
    col_id = columns.index('UT')
    col_begin_page = columns.index('BP')
    col_end_page = columns.index('EP')
    col_book_series = columns.index('BS')
    col_volume = columns.index('VL')
    col_issue = columns.index('IS')
    col_special_issue = columns.index('SI')
    col_supplement = columns.index('SU')
    for line in lines[1:]:
      data = line.split('\t')
      pub = Publication(data[col_title], Author.parse_sn_first_list(data[col_authors]), int(data[col_year]))
      if data[col_source]:
        pub.published_in = data[col_source]
      if data[col_book_series]:
        pub.series = data[col_book_series]
      if data[col_volume]:
        pub.volume = data[col_volume]
      pub.pages = make_page_range(data[col_begin_page], data[col_end_page])
      if data[col_issue]:
        pub.issue = data[col_issue]
      if data[col_special_issue]:
        pub.special_issue = data[col_special_issue]
      if data[col_supplement]:
        pub.supplement = data[col_supplement]
      if data[col_id]:
        pub.identifiers.append(Identifier(data[col_id], type='WOK'))
      if data[col_issn]:
        for issn in [x.strip() for x in data[col_issn].split(u';')]:
          pub.identifiers.append(Identifier(issn, type='ISSN'))
      if data[col_isbn]:
        for isbn in [x.strip() for x in data[col_isbn].split(u';')]:
          pub.identifiers.append(Identifier(isbn, type='ISBN'))
      if data[col_doi]:
        pub.identifiers.append(Identifier(data[col_doi], type='DOI'))
      yield pub
  
  def search_citations(self, publications):
    for publication in publications:
      ut = list(Identifier.find_by_type(publication.identifiers, 'WOK'))
      if len(ut) == 0:
        continue
      ut = ut[0].value.lstrip(u'WOS:')
      for cite_url in URL.find_by_type(publication.cite_urls, 'WOK'):
        for pub in self._get_citations_from_url(cite_url.value, ut):
          yield pub
  
  def assign_indexes(self, publication):
    pass
    
  def close(self):
    self.session.close()

class Wok(DataSource):
  def __init__(self, lamr=None):
    self.lamr = lamr
    self.ws = WokWS()
    self.web = WokWeb()
  
  def connect(self):
    return WokConnection(lamr=self.lamr, ws=self.ws, web=self.web)

class WokConnection(DataSourceConnection):
  def __init__(self, lamr=None, ws=None, web=None):
    self.lamr = lamr
    self.ws = ws
    self.web = web
    self._wsconn = None
    self._webconn = None
  
  @property
  def wsconn(self):
    if self._wsconn == None:
      self._wsconn = self.ws()
    return self._wsconn
  
  @property
  def webconn(self):
    if self._webconn == None:
      self._webconn = self.web()
    return self._webconn
  
  def search_by_author(self, surname, name=None, year=None):
    publications = list(self.wsconn.search_by_author(surname, name=name, year=year))
    self._retrieve_links(publications)
    return publications
  
  def search_citations(self, publications):
    citations = list(self.webconn.search_citations(publications))
    self.assign_indexes(citations)
    return citations
  
  def assign_indexes(self, publications):
    return self.wsconn.assign_indexes(publications)
  
  def close(self):
    if self._wsconn:
      self._wsconn.close()
    if self._webconn:
      self._webconn.close()
  
  def _retrieve_links(self, publications):
    if self.lamr is None:
      return
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
    with WokWS().connect() as wok:
      print_results(args, wok, wok._search(args.query))
  
  def retrieve(args):
    with WokWS().connect() as wok:
      print_results(args, wok, wok._retrieve_by_id(args.id).records)
  
  def search_by_author(args):
    if args.data_source == 'ws':
      ds = WokWS()
    else:
      ds = WokWeb()
    with ds.connect() as wok:
      for pub in wok.search_by_author(args.surname, name=args.name, year=args.year):
        print pub
  
  def services(args):
    with WokWS().connect() as wok:
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
  parser.add_argument('--data-source', choices=['ws', 'web'], default='ws', help='select data source implementation')
  
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
