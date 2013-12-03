# -*- coding: utf-8 -*-
import types
import re
from itertools import izip_longest
from util import normalize

def is_initial(name):
  if name.endswith('.'):
    return True
  if len(name) == 1:
    return True
  if name.isupper() and len(name) <= 3:
    return True
  return False

class Author(object):
  def __init__(self, surname, names=None, unparsed_text=None):
    if not isinstance(surname, types.StringTypes):
      raise TypeError('surname must be string')
    self.surname = surname
    if names == None:
      self.names = []
    elif isinstance(names, types.StringTypes):
      self.names = [names]
    else:
      self.names = list(names)
    self.unparsed_text = unparsed_text
  
  def __unicode__(self):
    return u' '.join(self.names + [self.surname])
  
  def __str__(self):
    return self.__unicode__().encode('UTF-8')
  
  def __repr__(self):
    r = 'Author({!r}'.format(self.surname)
    if len(self.names) > 0:
      r += ', names={!r}'.format(self.names)
    if self.unparsed_text:
      r += ', unparsed_text={!r}'.format(self.unparsed_text)
    r += ')'
    return r
  
  def to_dict(self):
    return {'names': self.names, 'surname': self.surname,
            'unparsed_text': self.unparsed_text}
  
  @classmethod
  def from_dict(cls, d):
    return cls(d['surname'], names=d['names'], unparsed_text=d.get('unparsed_text'))
  
  def __eq__(self, other):
    if not isinstance(other, Author):
      return NotImplemented
    if normalize(self.surname) != normalize(other.surname):
      return False
    if len(self.names) > 0 and len(other.names) > 0:
      if is_initial(self.names[0]) or is_initial(other.names[0]):
        return normalize(self.names[0][0]) == normalize(other.names[0][0])
      else:
        return normalize(self.names[0]) == normalize(other.names[0])
    return True
  
  def __hash__(self):
    """Hash musi zavisiet len na priezvisku, lebo to v niektorych pripadoch staci na to,
       aby sa dva Author objekty rovnali
    """
    return hash(normalize(self.surname))
  
  @property
  def formatted_surname(self):
    if self.surname.isupper():
      parts = self.surname.split()
      new_parts = []
      for part in parts:
        if part in [u'DE', u'VON']:
          new_parts.append(part.lower())
        elif part.startswith(u'MC'):
          new_parts.append(u'Mc' + part[2:].title())
        elif self.surname.startswith(u'MAC'):
          new_parts.append(u'Mac' + part[3:].title())
        else:
          new_parts.append(part.title())
      return u' '.join(new_parts)
    return self.surname
  
  @property
  def short_name(self):
    return u', '.join([self.formatted_surname,  u' '.join(name[0].upper() + u'.' for name in self.names)])
  
  @classmethod
  def parse_sn_first(cls, fullname):
    if ',' in fullname:
      parts = re.split(r'[,]+', fullname, maxsplit=1)
      surname = parts[0].strip()
      names = parts[1]
    else:
      parts = re.split(r'[ ]+', fullname)
      surname_parts = []
      surname_next = False
      consumed = False
      for i in range(len(parts)):
        if parts[i].endswith('.'):
          names = u' '.join(parts[i:])
          break
        if parts[i].lower() in [u'de', u'von']:
          surname_next = True
          surname_parts.append(parts[i])
          continue
        if surname_next:
          surname_parts.append(parts[i])
          surname_next = False
          continue
        if i == 0 or (not consumed and i != len(parts) -1 ):
          surname_parts.append(parts[i])
          consumed = True
          continue
        names = u' '.join(parts[i:])
        break
      else:
        names = ''
      surname = u' '.join(surname_parts)
    
    if len(names) > 0:
      name_parts = re.split(r'([. -]+)', names)
      names = []
      for name, separator in izip_longest(name_parts[::2], name_parts[1::2], fillvalue=''):
        if len(name) == 0:
          continue
        initial = '.' in separator
        # Osetrime inicialky, ak su napriklad Smith, JD
        if not surname.isupper() and name.isupper() and len(name) <= 3:
          for char in name:
            names.append(char + '.')
        else:
          names.append(name + ('.' if initial else ''))
    else:
      names = None
    return cls(surname, names, unparsed_text=fullname)
  
  @classmethod
  def parse_sn_first_list(cls, names, separator=u';'):
    return [cls.parse_sn_first(x.strip()) for x in names.split(separator)]

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
  
  def to_dict(self):
    return {'value': self.value, 'type': self.type, 'description': self.description}
  
  def __eq__(self, other):
    return self.type == other.type and self.value == other.value
  
  def __hash__(self):
    return hash((self.type, self.value))
  
  @classmethod
  def from_dict(cls, d):
    return cls(d['value'], type=d['type'], description=d['description'])
  
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

class Index(TaggedValue):
  pass

class Publication(object):
  def __init__(self, title, authors, year, published_in=None, pages=None, volume=None, series=None, issue=None, special_issue=None, supplement=None, source_urls=None, cite_urls=None, identifiers=None, errors=None, authors_incomplete=False, indexes=None, times_cited=None, article_no=None, publisher=None, publisher_city=None):
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
    authors_incomplete = zoznam autorov nie je uplny, obsahuje len par z nich
    indexes = v ktorych citacnych indexoch sa publikacia nachadza
    times_cited = pocet dokumentov citujucich tuto publikaciu
    article_no = Article Number
    """
    self.title = title
    self.authors = authors
    self.authors_incomplete = authors_incomplete
    self.year = year
    self.published_in = published_in
    self.pages = pages
    self.volume = volume
    self.series = series
    self.issue = issue
    self.special_issue = special_issue
    self.supplement = supplement
    self.times_cited = times_cited
    self.article_no = article_no
    self.publisher = publisher
    self.publisher_city = publisher_city
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
    if indexes == None:
      self.indexes = []
    else:
      self.indexes = list(indexes)
    if errors == None:
      self.errors = []
    else:
      self.errors = list(errors)
  
  def __unicode__(self):
    authors = u', '.join(unicode(x) for x in self.authors)
    if self.authors_incomplete:
      authors += u' et al.'
    source_urls = u' '.join(unicode(x) for x in self.source_urls)
    cite_urls = u' '.join(unicode(x) for x in self.cite_urls)
    identifiers = u' '.join(unicode(x) for x in self.identifiers)
    indexes = u' '.join(unicode(x) for x in self.indexes)
    
    r = u'{}\n'.format(self.title)
    r += u'  Publication year: {}\n'.format(self.year)
    r += u'  Authors: {}\n'.format(authors)
    if self.published_in:
      r += u'  Published in: {}\n'.format(self.published_in)
    if self.pages:
      r += u'  Pages: {}\n'.format(self.pages)
    if self.article_no:
      r += u'  Article No.: {}\n'.format(self.article_no)
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
    if self.publisher:
      r += u'  Publisher: {}\n'.format(self.publisher)
    if self.publisher_city:
      r += u'  Publisher city: {}\n'.format(self.publisher_city)
    r += u'  Source URLs: {}\n'.format(source_urls)
    r += u'  Citation list URLs: {}\n'.format(cite_urls)
    r += u'  Identifiers: {}\n'.format(identifiers)
    r += u'  Indexes: {}\n'.format(indexes)
    if self.times_cited:
      r += u'  Times cited: {}\n'.format(self.times_cited)
    if len(self.errors) > 0:
      errors = u' '.join(unicode(x) for x in self.errors)
      r += u'  Errors: {}\n'.format(errors)
    
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
    if len(self.errors) > 0:
      r += ', {}errors={}'.format(nl, reprlist(self.errors))
    if self.authors_incomplete:
      r += ', {}authors_incomplete=True'.format(nl)
    if len(self.indexes) > 0:
      r += ', {}indexes={}'.format(nl, reprlist(self.indexes))
    if self.times_cited != None:
      r += ', {}times_cited={}'.format(nl, self.times_cited)
    if self.article_no:
      r += ', {}article_no={!r}'.format(nl, self.article_no)
    if self.publisher:
      r += ', {}publisher={!r}'.format(nl, self.publisher)
    if self.publisher_city:
      r += ', {}publisher_city={!r}'.format(nl, self.publisher_city)
    r += nl + ')'
    return r

  def to_dict(self):
    def dictify(l):
      return [x.to_dict() for x in l]
    return {
      'title': self.title, 'authors': dictify(self.authors), 'year': self.year,
      'published_in': self.published_in, 'pages': self.pages, 'volume': self.volume,
      'series': self.series, 'issue': self.issue, 'special_issue': self.special_issue,
      'supplement': self.supplement, 'source_urls': dictify(self.source_urls),
      'cite_urls': dictify(self.cite_urls), 'identifiers': dictify(self.identifiers),
      'errors': self.errors, 'authors_incomplete': self.authors_incomplete,
      'indexes': dictify(self.indexes), 'times_cited': self.times_cited,
      'article_no': self.article_no, 'publisher': self.publisher, 'publisher_city': self.publisher_city
    }
  
  @classmethod
  def from_dict(cls, d):
    return Publication(
      d['title'], [Author.from_dict(x) for x in d['authors']], d['year'],
      published_in=d['published_in'], pages=d['pages'], volume=d['volume'],
      series=d['series'], issue=d['issue'], special_issue=d['special_issue'],
      supplement=d['supplement'], source_urls=[URL.from_dict(x) for x in d['source_urls']],
      cite_urls=[URL.from_dict(x) for x in d['cite_urls']],
      identifiers=[Identifier.from_dict(x) for x in d['identifiers']],
      errors=d['errors'], authors_incomplete=d['authors_incomplete'],
      indexes=[Index.from_dict(x) for x in d['indexes']], times_cited=d['times_cited'],
      article_no=d['article_no'], publisher=d.get('publisher'), publisher_city=d.get('publisher_city')
    )
  
  def __eq__(self, other):
    if self.year != other.year:
      return False
    if not self.authors_incomplete and not other.authors_incomplete and self.authors != other.authors:
      return False
    if normalize(self.title) != normalize(other.title):
      return False
    if normalize(self.article_no) != normalize(other.article_no):
      return False
    if normalize(self.pages) != normalize(other.pages):
      return False
    if normalize(self.volume) != normalize(other.volume):
      return False
    if normalize(self.issue) != normalize(other.issue):
      return False
    if normalize(self.published_in) != normalize(other.published_in):
      return False
    return True
  
  def in_index(self, *values):
    for index in self.indexes:
      if index.value in values:
        return True
    return False