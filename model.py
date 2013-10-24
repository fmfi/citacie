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
  
  def __repr__(self):
    r = 'Author({!r}'.format(self.surname)
    if len(self.names) > 0:
      r += ', names={!r}'.format(self.names)
    r += ')'
    return r

class TaggedValue(object):
  def __init__(self, value, type=None, description=None):
    """Reprezentuje hodnotu s typom
    
    value = string identifikator
    type = typ identifikatora (ISBN, ISSN, WOK, ...)
    description = pridany popis identifikatora, napriklad ak je viac roznych ISBN pre hardcover a paperback 
      verzie, da sa to popisat v tejto poznamke
    """
    self.value = value
    self.type = type
    self.description = description
  
  def __unicode__(self):
    r = u''
    if self.type:
      r += u'{}:'.format(self.type)
    r += self.value
    if self.description:
      r += u'({})'.format(self.description)
    return r
  
  def __str__(self):
    return self.__unicode__().encode('UTF-8')
  
  def __repr__(self):
    r = '{}({!r}'.format(type(self).__name__, self.value)
    if self.type:
      r += ', type={!r}'.format(self.type)
    if self.description:
      r += ', description={!r}'.format(self.description)
    r += ')'
    return r
  
  @staticmethod
  def find_by_type(iterable, type):
    return filter(lambda x: x.type == type, iterable)

class Identifier(TaggedValue):
  """Reprezentuje unikatny identifikator
  
  value = string identifikator
  type = typ identifikatora (ISBN, ISSN, WOK, ...)
  description = pridany popis identifikatora, napriklad ak je viac roznych ISBN pre hardcover a paperback 
    verzie, da sa to popisat v tejto poznamke
  """
  pass

class URL(TaggedValue):
  pass

class Publication(object):
  def __init__(self, title, authors, year, published_in=None, pages=None, volume=None, series=None, issue=None, special_issue=None, supplement=None, source_urls=None, cite_urls=None, identifiers=None):
    """Reprezentuje jednu publikaciu
    title = nazov publikacie
    authors = zoznam autorov publikacie
    year = rok vydania publikacie
    published_in = nazov casopisu/konferencie etc.
    pages = strany, na ktorych sa publikacia nachadza vramci published_in
    volume = volume casopisu
    series = nazov serie knih, kam patri published_in
    source_urls = adresy na zdrojove datbazy na webe
    cite_urls = adresy na zoznam citacii na webe
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
    if source_urls == None:
      self.source_urls = []
    else:
      self.source_urls = list(source_urls)
    if cite_urls == None:
      self.cite_urls = []
    else:
      self.cite_urls = list(cite_urls)
    if identifiers == None:
      self.identifiers = []
    else:
      self.identifiers = list(identifiers)
  
  def __unicode__(self):
    authors = u', '.join(unicode(x) for x in self.authors)
    source_urls = u' '.join(unicode(x) for x in self.source_urls)
    cite_urls = u' '.join(unicode(x) for x in self.cite_urls)
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
    r += u'  Source URLs: {}\n'.format(source_urls)
    r += u'  Citation list URLs: {}\n'.format(cite_urls)
    r += u'  Identifiers: {}\n'.format(identifiers)
    
    return r
  
  def __str__(self):
    return self.__unicode__().encode('UTF-8')
  
  def __repr__(self):
    return self.repr()
  
  def repr(self, pretty=False):
    def reprlist(l):
      if pretty:
        return '[' + ''.join('\n  ' + repr(x) + ', ' for x in l) + '\n]'
      else:
        return repr(l)
    
    if pretty:
      nl = '\n'
    else:
      nl = ''
    
    r = 'Publication({!r}, {}{}, {}{!r}'.format(self.title, nl, reprlist(self.authors), nl, self.year)
    
    if self.published_in:
      r += ', {}published_in={!r}'.format(nl, self.published_in)
    if self.pages:
      r += ', {}pages={!r}'.format(nl, self.pages)
    if self.volume:
      r += ', {}volume={!r}'.format(nl, self.volume)
    if self.series:
      r += ', {}series={!r}'.format(nl, self.series)
    if self.issue:
      r += ', {}issue={!r}'.format(nl, self.issue)
    if self.special_issue:
      r += ', {}special_issue={!r}'.format(nl, self.special_issue)
    if self.supplement:
      r += ', {}supplement={!r}'.format(nl, self.supplement)
    if len(self.source_urls) > 0:
      r += ', {}source_urls={}'.format(nl, reprlist(self.source_urls))
    if len(self.cite_urls) > 0:
      r += ', {}cite_urls={}'.format(nl, reprlist(self.cite_urls))
    if len(self.identifiers) > 0:
      r += ', {}identifiers={}'.format(nl, reprlist(self.identifiers))
    r += nl + ')'
    return r
