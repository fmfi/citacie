# -*- coding: utf-8 -*-
from data_source import DataSource, DataSourceConnection

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
    for data_source in self.data_sources: # TODO move to connection setup to __enter__
      with data_source() as conn:
        for pub in conn.search_citations(publications):
          yield pub # TODO merge publications
  
  def assign_indexes(self, publications):
    for data_source in self.data_sources: # TODO move to connection setup to __enter__
      with data_source() as conn:
        conn.assign_indexes(publications)
  
  def close(self):
    pass # TODO close connections created in __enter__