# -*- coding: utf-8 -*-
from data_source import DataSource, DataSourceConnection
from model import Publication, Author, Identifier, URL, Index
import htmlform

from collections import OrderedDict
from urllib import urlencode, quote
import requests
import time
import html5lib

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
    
    self._delay()
    r_results = self.session.post(post_url, data=data, headers=headers)
    
    et = html5lib.parse(r_results.text, treebuilder="lxml")
    authors_form = et.find("//{http://www.w3.org/1999/xhtml}form[@name='AuthorLookupResultsForm']")
    
    data2 = htmlform.find_attributes(authors_form, include_cb=['allField', 'authorIds'])
    data2.append(('showDocumentsButton.x', '0'))
    data2.append(('showDocumentsButton.y', '0'))
    
    headers = {'Referer': r_form.url}
    
    self._delay()
    r_results2 = self.session.post(post2_url, data=data2, headers=headers)
    
    print r_results2.text.encode('UTF-8')
    
    return []
  
  def search_citations(self, publications):
    
    return []
  
  def assign_indexes(self, publication):
    pass
  
  def close(self):
    self.session.close()

if __name__ == '__main__':
  with ScopusWeb().connect() as conn:
    for pub in conn.search_by_author('Vinar', name='T'):
      print pub