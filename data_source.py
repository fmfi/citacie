# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod

class DataSource(object):
  __metaclass__ = ABCMeta
  
  @abstractmethod
  def connect(self):
    raise NotImplemented
  
  def __call__(self):
    return self.connect()
  
class DataSourceConnection(object):
  __metaclass__ = ABCMeta
  
  @abstractmethod
  def search_by_author(self, surname, name=None, year=None):
    raise NotImplemented
  
  @abstractmethod
  def close(self):
    raise NotImplemented
  
  def __enter__(self):
    return self
  
  def __exit__(self, type, value, traceback):
    self.close()
    return False