# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod

class DataSource(object):
  __metaclass__ = ABCMeta
  
  @abstractmethod
  def connect(self):
    """Vyrobi novy connection objekt pre dany data source, ak by nahodou bolo
       treba rozne connection v roznych threadoch, malo by to vzdy vracat novu
       (alebo nepouzivanu poolovanu) instanciu
    """
    raise NotImplemented
  
  def __call__(self):
    return self.connect()
  
class DataSourceConnection(object):
  __metaclass__ = ABCMeta
  
  @abstractmethod
  def search_by_author(self, surname, name=None, year=None):
    """Vrati iterator vracajuci zoznam publikacii pre dane meno a rok
       - priezvisko hlada presne
       - meno hlada ako prefix (t.j. T najde aj Tomas)
       - ak je rok zadany, vracia len zaznamy pre dany rok, inak pre vsetky roky
    """
    raise NotImplemented
  
  @abstractmethod
  def search_citations(self, publications):
    """Vrati iterator vracajuci zoznam publikacii, ktore cituju publikacie
       v zozname publications
    """
    raise NotImplemented
  
  @abstractmethod
  def assign_indexes(self, publication):
    """Zisti a nastavi, v akych indexoch sa publikacia nachadza
    """
    raise NotImplemented
  
  @abstractmethod
  def close(self):
    """Uvolni zdroje pouzivane tymto objektom"""
    raise NotImplemented
  
  def __enter__(self):
    return self
  
  def __exit__(self, type, value, traceback):
    self.close()
    return False
