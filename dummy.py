# -*- coding: utf-8 -*-
"""Modul, ktory vracia testovacie data"""

from model import *
import names as name_generator
import random

random.seed(11248384923432943290)

# Vygenerujme n nahodnych mien
names_count = 2000
names = []
for i in range(names_count):
  gender = random.choice(('male', 'female'))
  name = []
  for j in range(random.randint(1,3)):
    name.append(unicode(name_generator.get_first_name(gender=gender)))
  surname = unicode(name_generator.get_last_name())
  names.append((name, surname))

def random_author(name=None):
  if name == None:
    name = random.choice(names)
  given_names, surname = name
  name_type = random.choice(('single', 'initial', 'single+initial', 'full'))
  if name_type == 'single':
    return Author(surname, names=[given_names[0]])
  elif name_type == 'initial':
    dot = random.choice(('.', ''))
    return Author(surname, names=[given_names[0][0] + dot])
  elif name_type == 'single+initial':
    dot = random.choice(('.', ''))
    other_names = [x[0] + dot for x in given_names[1:]]
    return Author(surname, names=[given_names[0]] + other_names)
  elif name_type == 'full':
    return Author(surname, names=given_names)

publication_count = 1000
publications = []
for i in range(publication_count):
  title = u'Publication {}'.format(i)
  r = 1000 if random.randint(1, 3) == 1 else 10
  author_count = random.randint(1, r)
  authors = [random_author(name) for name in random.sample(names, author_count)]
  year = random.randint(2000, 2013)
  pub = Publication(title, authors, year)
  publications.append(pub)

class Dummy:
  def open(self):
    pass
  
  def search_by_author(self, surname, name=None, year=None):
    surname = surname.lower()
    if name:
      name = name.lower()
    if year:
      year = int(year)
    def matches(pub):
      if year != None:
        if pub.year != year:
          return False
      for author in pub.authors:
        if author.surname.lower() != surname:
          continue
        if not name:
          return True
        found = False
        for aname in author.names:
          if aname.lower().startswith(name):
            found = True
            break
        if not found:
          continue
        return True
      return False
    return [pub for pub in publications if matches(pub)]
    
  def close(self):
    pass
  
  def __enter__(self):
    return self
  
  def __exit__(self, type, value, traceback):
    return False

if __name__ == '__main__':
  print names
  for i in range(10):
    print random_author()