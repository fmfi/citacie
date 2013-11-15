#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from flask import Flask
app = Flask(__name__)

from flask import render_template
from flask import request

from werkzeug.exceptions import BadRequest
from itsdangerous import URLSafeSerializer

from model import Identifier, Publication

from local_settings import active_config
config = active_config(app)

serializer = URLSafeSerializer(config.secret)

import titlecase
app.jinja_env.filters['titlecase'] = titlecase.titlecase


@app.route('/')
def index():
  return render_template('index.html')

@app.route('/search-by-author')
def search_by_author():
  name = request.args.get('name', '')
  surname = request.args.get('surname', '')
  year = request.args.get('year', '')
  
  if len(name) == 0:
    name = None
  
  if len(surname) == 0:
    raise BadRequest()
  
  if len(year) > 0:
    if not re.match(r'^\d*$', year):
      raise BadRequest()
  else:
    year = None
  
  results = []
  for data_source in config.data_sources:
    with data_source() as conn:
      results.extend(conn.search_by_author(surname, name=name, year=year))
  
  results.sort(key=lambda r: r.title.lower())
  results.sort(key=lambda r: r.year, reverse=True)
  
  for result in results:
    result.serialized = serializer.dumps(result.to_dict())
  
  return render_template('search-by-author.html',
    search_name=name, search_surname=surname, search_year=year,
    results=results)

@app.route('/search-citations', methods=['POST'])
def search_citations():
  pubs = [Publication.from_dict(serializer.loads(x)) for x in request.form.getlist('publication')]
  
  for data_source in config.data_sources:
    with data_source() as conn:
      for pub in pubs:
        conn.assign_indexes(pub)
  
  citing_pubs = []  
  for data_source in config.cite_data_sources:
    with data_source() as conn:
      citing_pubs.extend(conn.search_citations(pubs))
  
  def get_first_author_surname(pub):
    if len(pub.authors) == 0:
      return None
    return pub.authors[0].surname.lower()
  
  pubs_authors = set()
  for pub in pubs:
    pubs_authors.update(pub.authors)
  
  all_authors = set()
  all_authors.update(pubs_authors)
  for pub in citing_pubs:
    all_authors.update(pub.authors)
  
  for pub in citing_pubs:
    pub.autocit = pubs_authors.intersection(pub.authors)
  
  citing_pubs = [pub for pub in citing_pubs if not pub.autocit]
  
  citing_pubs.sort(key=get_first_author_surname)
  citing_pubs.sort(key=lambda r: r.year)
  
  return render_template('search-citations.html', query_pubs=pubs, results=citing_pubs, authors=sorted(list(all_authors), key=lambda x: x.surname))

if __name__ == '__main__':
  import os
  if 'CITACIE_DEBUG' in os.environ:
    app.debug = True
  app.run()
