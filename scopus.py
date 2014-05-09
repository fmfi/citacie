# -*- coding: utf-8 -*-
from data_source import DataSource, DataSourceConnection
from model import Publication, Author, Identifier, URL, Index
from htmlform import HTMLForm
from util import strip_bom, make_page_range
from throttle import ThreadingThrottler

from collections import OrderedDict
from urllib import urlencode, quote
import requests
from requests.utils import add_dict_to_cookiejar
import html5lib
import unicodecsv
from urlparse import urlparse, parse_qs
import re
import logging

class ScopusWeb(DataSource):
  def __init__(self, additional_headers=None, throttler=None, proxies=None):
    if additional_headers == None:
      additional_headers = {'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0'}
    self.additional_headers = additional_headers
    self.proxies = proxies
    if throttler == None:
      throttler = ThreadingThrottler(number=1, period=1, min_delay=1, finished_delay=0.5, timeout=60)
    self.throttler = throttler
    
  def connect(self):
    return ScopusWebConnection(self.throttler, additional_headers=self.additional_headers, proxies=self.proxies)
  
class ScopusWebConnection(DataSourceConnection):
  def __init__(self, throttler, additional_headers=None, proxies=None):
    self.additional_headers = additional_headers
    self.session = requests.Session()
    if additional_headers:
      self.session.headers.update(additional_headers)
    if proxies:
      self.session.proxies.update(proxies)
    self.throttler = throttler
  
  def search_by_author_old(self, surname, name=None, year=None):
    form_url = 'http://www.scopus.com/search/form.url?display=authorLookup'
    post_url = 'http://www.scopus.com/search/submit/authorlookup.url'
    post2_url = 'http://www.scopus.com/results/authorLookup.url'
    
    with self.throttler():
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
    
    with self.throttler():
      r_results = self.session.post(post_url, data=data, headers=headers)
    
    et = html5lib.parse(r_results.text, treebuilder="lxml")
    
    namespaces = {'html': 'http://www.w3.org/1999/xhtml'}
    errors = et.xpath(".//html:form[@name='AuthorLookupResultsForm']//*[contains(concat(' ', normalize-space(@class), ' '), ' errText ')]", namespaces=namespaces)

    for error in errors:
      if error.text.strip() == 'No authors were found':
        return
      raise IOError('Error encountered during author search: ' + error.text.strip())
    
    authors_form = et.find("//{http://www.w3.org/1999/xhtml}form[@name='AuthorLookupResultsForm']")
    
    form2 = HTMLForm(authors_form)
    for cb in ['allField', 'pageField', 'allField2', 'pageField2']:
      form2[cb].checked = True
    form2.check_all('authorIds')
    form2.set_value('selectDeselectAllAttempt', 'clicked')
    form2.set_value('clickedLink', 'ShowDocumentsButton')
    
    headers = {'Referer': r_results.url}
    
    with self.throttler():
      r_results2 = self.session.post(post2_url, data=form2.to_params(), headers=headers)
    
    for pub in self._download_from_results_form(r_results2, context=['_search_by_author', surname, name]):
      if year == None or pub.year == year:
        yield pub
  
  def search_by_author(self, surname, name=None, year=None):
    form_url = 'http://www.scopus.com'
    post_url = 'http://www.scopus.com/search/submit/basic.url'
    
    with self.throttler():
      r_form = self.session.get(form_url)
    
    add_dict_to_cookiejar(self.session.cookies, {'javaScript': 'true', 'xmlHttpRequest': 'true'})
    
    et = html5lib.parse(r_form.text, treebuilder="lxml")
    namespaces = {'html': 'http://www.w3.org/1999/xhtml'}
    search_form_html = et.find("//{http://www.w3.org/1999/xhtml}form[@name='BasicValidatedSearchForm']")
    
    search_form = HTMLForm(search_form_html)
    search_term = surname
    if name:
      search_term += u', {}'.format(name)
    search_form.set_value('searchterm1', search_term)
    search_form.set_value('field1', 'AUTHOR-NAME')
    if year != None:
      search_form.set_value('yearFrom', str(year))
      search_form.set_value('yearTo', str(year))
      search_form.set_value('dateType', 'Publication_Date_Type')
    
    headers = {'Referer': r_form.url}
    
    with self.throttler():
      r_results = self.session.post(post_url, data=search_form.to_params(), headers=headers)
    
    et = html5lib.parse(r_results.text, treebuilder="lxml")
    namespaces = {'html': 'http://www.w3.org/1999/xhtml'}
    errors = et.xpath(".//html:form[@name='SearchResultsForm']//*[contains(concat(' ', normalize-space(@class), ' '), ' errText ')]", namespaces=namespaces)

    for error in errors:
      if error.text.strip() == 'No results were found.':
        return []
      raise IOError('Error encountered during document search: ' + error.text.strip())
    
    return self._download_from_results_form(r_results, context=['_search_by_author', surname, name, year])

  def _download_from_results_form(self, results_form_response, context=None):
    handle_results_url = 'http://www.scopus.com/results/handle.url'
    
    et = html5lib.parse(results_form_response.text, treebuilder="lxml")
    results_form = et.find("//{http://www.w3.org/1999/xhtml}form[@name='SearchResultsForm']")
    form = HTMLForm(results_form)
    
    form.check_all('selectedEIDs')
    form.set_value('selectDeselectAllAttempt', 'clicked')
    form.set_value('clickedLink', 'Export')
    form.check_all('selectAllCheckBox')
    form.check_all('selectPageCheckBox')
    
    headers = {'Referer': results_form_response.url}
    
    with self.throttler():
      r_results3 = self.session.post(handle_results_url, data=form.to_params(), headers=headers)
    
    return self._download_from_export_form(r_results3, context=context)
  
  def _download_from_export_form(self, export_form_response, context=None):
    export_url = 'http://www.scopus.com/onclick/export.url'
    
    et = html5lib.parse(export_form_response.text, treebuilder="lxml")
    export_form = et.find("//{http://www.w3.org/1999/xhtml}form[@name='exportForm']")

    if export_form is None:
        return []

    form = HTMLForm(export_form)

   #form.set_value('exportFormat', 'CSV')
   #form.set_value('view', 'SpecifyFields')
   #form.check('selectedOtherInformationItems', ['Conference information'])
   #form.check_all('selectedCitationInformationItemsAll')
   #form.check('selectedCitationInformationItems', [
   #  'Author(s)', 'Document title', 'Year', 'Source title',
   #  'Volume, Issue, Pages', 'Citation count', 'Source and Document Type'
   #])
   #form.check('selectedBibliographicalInformationItems', [
   #  'Serial identifiers (e.g. ISSN)', 'DOI', 'Publisher'
   #])
    form.set_value('oneClickExport', '{"Format":"CSV","SelectedFields":"Link Authors Title Year SourceTitle Volume Issue ArtNo PageStart PageEnd PageCount DocumentType CitedBy Source ISSN ISBN CODE  DOI Publisher ","View":"SpecifyFields"}')
    
    headers = {'Referer': export_form_response.url}
    with self.throttler():
      csv = self.session.get(export_url, params=form.to_params(), headers=headers)
    
    self._log_csv(context, csv.content, encoding=csv.encoding)
    
    return self._parse_csv(csv.content, encoding=csv.encoding)
  
  def _log_csv(self, context, content, encoding='UTF-8'):
    pass
  
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
    
    def to_num(x):
      x = x.strip()
      if len(x) == 0:
        return 0
      return int(x)
    
    for line in csv:
      if line['Authors'] == '[No author name available]':
        authors = []
      else:
        authors = Author.parse_sn_first_list(line['Authors'], separator=u',')
      pub = Publication(line['Title'], authors, to_num(line['Year']))
      source_title = empty_to_none(line['Source title'])
      if source_title:
        source_title, replacements = re.subn(r' \(including subseries [^)]+\)', '', source_title)
        source_title = source_title.strip()
        if replacements:
          pub.series = source_title
        else:
          pub.published_in = source_title
      pub.volume = empty_to_none(line['Volume'])
      pub.issue = empty_to_none(line['Issue'])
      pub.pages = make_page_range(empty_to_none(line['Page start']), empty_to_none(line['Page end']))

      # (mrshu): z dovodu, ktory nedokazem pochopit teraz SCOPUS vracia cosi
      # ako 'Cited byLink', kde da dohromady tieto dva fieldy. Nepodarilo sa mi
      # prist na to ako to spravit rozumnejsie, tento hack to aspon rozparsuje
      splits = line['Cited byLink'].split('"')
      if len(splits) > 1:
          line['Link'] = splits[1]
          line['Cited by'] = splits[0]
      else:
          line['Link'] = splits[0]
          line['Cited by'] = None

      pub.times_cited = empty_to_none(line['Cited by'])
      pub.article_no = empty_to_none(line['Art. No.'])
      pub.publisher = empty_to_none(line['Publisher'])
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
    for publication in publications:
      eid = list(Identifier.find_by_type(publication.identifiers, 'SCOPUS'))
      if len(eid) == 0:
        continue
      eid = eid[0].value
      detail_url = list(URL.find_by_type(publication.source_urls, 'SCOPUS'))
      if len(detail_url) == 0:
        continue
      detail_url = detail_url[0].value
      for pub in self._get_citations_from_detail_url(detail_url, eid):
        yield pub
  
  def _get_citations_from_detail_url(self, detail_url, eid):
    add_dict_to_cookiejar(self.session.cookies, {'javaScript': 'true'})
    with self.throttler():
      r = self.session.get(detail_url)
    
    et = html5lib.parse(r.text, treebuilder="lxml")
    
    def get_cited_by_link(et):
      namespaces = {'html': 'http://www.w3.org/1999/xhtml'}
      cite_links = et.xpath(".//html:a[starts-with(@href, 'http://www.scopus.com/search/submit/citedby.url') and @title='View all citing documents']", namespaces=namespaces)
      
      for link in cite_links:
        if 'title' in link.attrib:
          logging.debug('Trying citation link: %s', link.attrib['title'])
          return link.attrib['href']
      
      return None
    
    link = get_cited_by_link(et)
    if link == None:
      logging.warning('No SCOPUS citation link found')
      return []
    
    headers = {'Referer': r.url}
    
    with self.throttler():
      r2 = self.session.get(link, headers=headers)
    
    return self._download_from_results_form(r2, context=['_get_citations_from_detail_url', detail_url, eid])
    
  
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
