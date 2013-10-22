# -*- coding: utf-8 -*-
"""Modul, ktory vracia testovacie data"""

class Dummy:
  def __init__(self, pubs):
    self.pubs = pubs
  
  def open(self):
    pass
  
  def search_by_author(self, surname, name=None, year=None):
    return self.pubs
    
  def close(self):
    pass
  
  def __enter__(self):
    return self
  
  def __exit__(self, type, value, traceback):
    return False

