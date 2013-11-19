# -*- coding: utf-8 -*-
from data_source import DataSource, DataSourceConnection
from model import Publication

class Merge(DataSource):
  def __init__(self, *data_sources):
    self.data_sources = data_sources
    
  def connect(self):
    return MergeConnection(self.data_sources)
  
class MergeConnection(DataSourceConnection):
  def __init__(self, data_sources):
    self.data_sources = data_sources
  
  def search_by_author(self, surname, name=None, year=None):
    for data_source in self.data_sources: # TODO move to connection setup to __enter__
      with data_source() as conn:
        for pub in conn.search_by_author(surname, name=name, year=None):
          yield pub
  
  def search_citations(self, publications):
    cit = []
    for data_source in self.data_sources: # TODO move to connection setup to __enter__
      with data_source() as conn:
        cit.extend(list(conn.search_citations(publications)))
    
    cit.sort(key=lambda r: r.title)
    cit.sort(key=lambda r: r.year)
    
    merged = []
    
    while len(cit) > 0:
      cur = cit.pop(0)
      bucket = [cur]
      for i in xrange(len(cit) - 1, -1, -1):
        if cit[i] == cur:
          bucket.append(cit[i])
          del cit[i]
      def find_longest(attr):
        longest = None
        for p in bucket:
          v = getattr(p, attr)
          if v != None:
            if longest == None:
              longest = (p, v)
            elif len(v) > len(longest):
              longest = (p, v)
        if longest == None:
          return (None, None)
        return longest
      lauthors_pub, lauthors = find_longest('authors')
      mpub = Publication(find_longest('title')[1], lauthors, cur.year)
      mpub.published_in = find_longest('published_in')[1]
      mpub.series = find_longest('series')[1]
      mpub.pages = find_longest('pages')[1]
      mpub.volume = find_longest('volume')[1]
      mpub.source_urls = list(set([x for p in bucket for x in p.source_urls]))
      mpub.cite_urls = list(set([x for p in bucket for x in p.cite_urls]))
      mpub.authors_incomplete = lauthors_pub.authors_incomplete
      mpub.indexes = list(set([x for p in bucket for x in p.indexes]))
      mpub.times_cited = max(p.times_cited for p in bucket)
      mpub.merge_sources = bucket
      merged.append(mpub)
    
    return merged
  
  def assign_indexes(self, publications):
    for data_source in self.data_sources: # TODO move to connection setup to __enter__
      with data_source() as conn:
        conn.assign_indexes(publications)
  
  def close(self):
    pass # TODO close connections created in __enter__