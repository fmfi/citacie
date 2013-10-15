# -*- coding: utf-8 -*-
import types

class Author(object):
  def __init__(self, surname, names=None):
    if not isinstance(surname, types.StringTypes):
      raise TypeError('surname must be string')
    self.surname = surname
    if names == None:
      self.names = []
    elif isinstance(names, types.StringTypes):
      self.names = [names]
    else:
      self.names = list(names)
  
  def __unicode__(self):
    return u' '.join(self.names + [self.surname])
  
  def __str__(self):
    return self.__unicode__().encode('UTF-8')

class Identifier(object):
  def __init__(self, id, type=None, description=None):
    """Reprezentuje jednoznacny identifikator
    
    id = string identifikator
    type = typ identifikatora (ISBN, ISSN, WOK, ...)
    description = pridany popis identifikatora, napriklad ak je viac roznych ISBN pre hardcover a paperback 
      verzie, da sa to popisat v tejto poznamke
    """
    self.id = id
    self.type = type
    self.description = description
  
  def __unicode__(self):
    r = u''
    if self.type:
      r += u'{}:'.format(self.type)
    r += self.id
    if self.description:
      r += u'({})'.format(self.description)
    return r
  
  def __str__(self):
    return self.__unicode__().encode('UTF-8')

class Publication(object):
  def __init__(self, title, authors, year, published_in=None, pages=None, volume=None, series=None, issue=None, special_issue=None, supplement=None, urls=None, identifiers=None):
    """Reprezentuje jednu publikaciu
    title = nazov publikacie
    authors = zoznam autorov publikacie
    year = rok vydania publikacie
    published_in = nazov casopisu/konferencie etc.
    pages = strany, na ktorych sa publikacia nachadza vramci published_in
    volume = volume casopisu
    series = nazov serie knih, kam patri published_in
    urls = adresy na zdrojove datbazy na webe
    identifiers = identifikatory tejto publikacie
    """
    self.title = title
    self.authors = authors
    self.year = year
    self.published_in = published_in
    self.pages = pages
    self.volume = volume
    self.series = series
    self.issue = issue
    self.special_issue = special_issue
    self.supplement = supplement
    if urls == None:
      self.urls = []
    elif isinstance(urls, types.StringTypes):
      self.urls = [urls]
    else:
      self.urls = list(urls)
    if identifiers == None:
      self.identifiers = []
    elif isinstance(identifiers, Identifier):
      self.identifiers = [identifiers]
    else:
      self.identifiers = list(identifiers)
  
  def __unicode__(self):
    authors = u', '.join(unicode(x) for x in self.authors)
    urls = u' '.join(unicode(x) for x in self.urls)
    identifiers = u' '.join(unicode(x) for x in self.identifiers)
    
    r = u'{}\n'.format(self.title)
    r += u'  Publication year: {}\n'.format(self.year)
    r += u'  Authors: {}\n'.format(authors)
    if self.published_in:
      r += u'  Published in: {}\n'.format(self.published_in)
    if self.pages:
      r += u'  Pages: {}\n'.format(self.pages)
    if self.issue:
      r += u'  Issue: {}\n'.format(self.issue)
    if self.special_issue:
      r += u'  Special issue: {}\n'.format(self.special_issue)
    if self.supplement:
      r += u'  Supplement: {}\n'.format(self.supplement)
    if self.volume:
      r += u'  Volume: {}\n'.format(self.volume)
    if self.series:
      r += u'  Series: {}\n'.format(self.series)
    r += u'  Source URLs: {}\n'.format(urls)
    r += u'  Identifiers: {}\n'.format(identifiers)
    
    return r
  
  def __str__(self):
    return self.__unicode__().encode('UTF-8')