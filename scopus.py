# -*- coding: utf-8 -*-
from data_source import DataSource, DataSourceConnection
from model import Publication, Author, Identifier, URL, Index
from htmlform import HTMLForm
from util import strip_bom, make_page_range

from collections import OrderedDict
from urllib import urlencode, quote
import requests
from requests.utils import add_dict_to_cookiejar
import time
import html5lib
import unicodecsv
from urlparse import urlparse, parse_qs

class ScopusWeb(DataSource):
  def __init__(self, additional_headers=None):
    if additional_headers == None:
      additional_headers = {'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0'}
    self.additional_headers = additional_headers
    
  def connect(self):
    return ScopusWebConnection(additional_headers=self.additional_headers)
  
class ScopusWebConnection(DataSourceConnection):
  def __init__(self, additional_headers=None):
    self.additional_headers = additional_headers
    self.session = requests.Session()
    if additional_headers:
      self.session.headers.update(additional_headers)
  
  def _delay(self):
    time.sleep(1)
  
  def search_by_author(self, surname, name=None, year=None):
    form_url = 'http://www.scopus.com/search/form.url?display=authorLookup'
    post_url = 'http://www.scopus.com/search/submit/authorlookup.url'
    post2_url = 'http://www.scopus.com/results/authorLookup.url'
    post3_url = 'http://www.scopus.com/results/handle.url'
    get4_url = 'http://www.scopus.com/citation/export.url'
    
    r_form = self.session.get(form_url)
    
    data = [
      ('origin', 'searchauthorlookup'),
      ('src', ''),
      ('edit', ''),
      ('poppUp', ''),
      ('basicTab', ''),
      ('advancedTab', ''),
      ('searchterm1', surname),
      ('searchterm2', name if name else ''),
      ('institute', ''),
      ('submitButtonName', 'Search'),
      ('authSubject', 'LFSC'),
      ('authSubject', 'HLSC'),
      ('authSubject', 'PHSC'),
      ('authSubject', 'SOSC'),
      ('submitButtonName', 'Search'),
    ]
    
    headers = {'Referer': r_form.url}
    add_dict_to_cookiejar(self.session.cookies, {'javaScript': 'true'})
    
    self._delay()
    r_results = self.session.post(post_url, data=data, headers=headers)
    
    et = html5lib.parse(r_results.text, treebuilder="lxml")
    authors_form = et.find("//{http://www.w3.org/1999/xhtml}form[@name='AuthorLookupResultsForm']")
    
    form2 = HTMLForm(authors_form)
    for cb in ['allField', 'pageField', 'allField2', 'pageField2']:
      form2[cb].checked = True
    form2.check_all('authorIds')
    form2.set_value('selectDeselectAllAttempt', 'clicked')
    form2.set_value('clickedLink', 'ShowDocumentsButton')
    
    headers = {'Referer': r_results.url}
    
    self._delay()
    r_results2 = self.session.post(post2_url, data=form2.to_params(), headers=headers)
    
    et = html5lib.parse(r_results2.text, treebuilder="lxml")
    results_form = et.find("//{http://www.w3.org/1999/xhtml}form[@name='SearchResultsForm']")
    form3 = HTMLForm(results_form)
    
    form3.check_all('selectedEIDs')
    form3.set_value('selectDeselectAllAttempt', 'clicked')
    form3.set_value('clickedLink', 'Export')
    form3.check_all('selectAllCheckBox')
    form3.check_all('selectPageCheckBox')
    
    self._delay()
    headers = {'Referer': r_results2.url}
    r_results3 = self.session.post(post3_url, data=form3.to_params(), headers=headers)
    
    et = html5lib.parse(r_results3.text, treebuilder="lxml")
    export_form = et.find("//{http://www.w3.org/1999/xhtml}form[@name='exportForm']")
    form4 = HTMLForm(export_form)
    
    form4.set_value('exportFormat', 'CSV')
    form4.set_value('view', 'FullDocument')
    
    self._delay()
    headers = {'Referer': r_results3.url}
    r_results4 = self.session.get(get4_url, params=form4.to_params(), headers=headers)
    
    return self._parse_csv(r_results4.content, encoding=r_results4.encoding)
  
  def _parse_csv(self, content, encoding='UTF-8'):
    csv = unicodecsv.DictReader(strip_bom(content).splitlines(), encoding=encoding)
    
    def empty_to_none(s):
      if s == None:
        return None
      s = s.strip()
      if len(s) == 0:
        return None
      return s
    
    def list_remove_empty(l):
      r = []
      for x in l:
        v = empty_to_none(x)
        if v:
          r.append(v)
      return r
    
    for line in csv:
      authors = Author.parse_sn_first_list(line['Authors'], separator=u',')
      pub = Publication(line['Title'], authors, int(line['Year']))
      pub.published_in = empty_to_none(line['Source title'])
      pub.volume = empty_to_none(line['Volume'])
      pub.issue = empty_to_none(line['Issue'])
      pub.pages = make_page_range(empty_to_none(line['Page start']), empty_to_none(line['Page end']))
      url = empty_to_none(line['Link'])
      
      if url:
        pub.source_urls.append(URL(url, type='SCOPUS', description='SCOPUS'))
        url_parts = urlparse(url)
        url_query = parse_qs(url_parts.query)
        if 'eid' in url_query and len:
          pub.identifiers.append(Identifier(url_query['eid'][0], type='SCOPUS'))
      
      for issn in list_remove_empty(line['ISSN'].split(u';')):
        pub.identifiers.append(Identifier(issn, type='ISSN'))
      
      for isbn in list_remove_empty(line['ISBN'].split(u';')):
        pub.identifiers.append(Identifier(isbn, type='ISBN'))
      
      doi = empty_to_none(line['DOI'])
      if doi:
        pub.identifiers.append(Identifier(doi, type='DOI'))
      
      pub.indexes.append(Index('SCOPUS', type='SCOPUS'))
      
      yield pub
  
  def search_citations(self, publications):
    
    return []
  
  def assign_indexes(self, publications):
    pass
  
  def close(self):
    self.session.close()

if __name__ == '__main__':
  with ScopusWeb().connect() as conn:
    #for pub in conn.search_by_author('Vinar', name='T'):
    with open('sc-csv.csv', 'r') as f:
      for pub in conn._parse_csv(f.read()):
        print pub