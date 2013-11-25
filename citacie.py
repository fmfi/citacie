#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from flask import Flask
app = Flask(__name__)

from flask import render_template
from flask import request
from flask import Response
from flask import stream_with_context

from werkzeug.exceptions import BadRequest
from itsdangerous import URLSafeSerializer

from model import Identifier, Publication
import os
import util

from collections import namedtuple

if 'CITACIE_DEBUG' in os.environ:
  app.debug = True

from local_settings import active_config
config = active_config(app)

serializer = URLSafeSerializer(config.secret)

import titlecase
def filter_titlecase(text, all_caps_only=False):
  if all_caps_only and not titlecase.ALL_CAPS.match(text):
    return text
  return titlecase.titlecase(text)
app.jinja_env.filters['titlecase'] = filter_titlecase
def filter_tagtype(it, typ):
  return [tag for tag in it if tag.type == typ]
app.jinja_env.filters['tagtype'] = filter_tagtype
app.jinja_env.filters['remove_proceedings'] = util.remove_proceedings

def stream_template(template_name, **context):
  def buffer_generator(gen):
    buf = []
    for item in gen:
      if isinstance(item, Flush):
        yield u''.join(buf)
        del buf[:]
      else:
        buf.append(item)
    if len(buf):
      yield u''.join(buf)
  app.update_template_context(context)
  t = app.jinja_env.get_template(template_name)
  rv = stream_with_context(buffer_generator(t.generate(context)))
  return Response(rv)

from jinja2 import nodes
from jinja2.ext import Extension

class Flush(object):
  pass

class FlushExtension(Extension):
  tags = set(['flush'])

  def parse(self, parser):
    lineno = parser.stream.next().lineno
    return nodes.CallBlock(self.call_method('_flush', []),
                            [], [], []).set_lineno(lineno)

  def _flush(self, caller):
    return Flush()

app.jinja_env.add_extension(FlushExtension)

class DelayedResult(object):
  def __init__(self, result=None, is_error=False):
    self.is_error = is_error
    self.result = result

def delayed(fn):
  def d():
    try:
      return DelayedResult(result=fn())
    except:
      app.logger.exception('Exception in delayed handler')
      return DelayedResult(is_error=True)
  return d

@app.route('/')
def index():
  return stream_template('index.html')

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
    year = int(year)
  else:
    year = None
  
  @delayed
  def get_results():
    with config.data_source() as conn:
      results = list(conn.search_by_author(surname, name=name, year=year))
    
    results.sort(key=lambda r: r.title.lower())
    results.sort(key=lambda r: r.year)
    
    for result in results:
      result.serialized = serializer.dumps(result.to_dict())
    
    return results
  
  return stream_template('search-by-author.html',
    search_name=name, search_surname=surname, search_year=year,
    get_results=get_results)

SearchCitationsResult = namedtuple('SearchCitationsResult', ['citations', 'autocitation_count', 'autocitation_count_by_index'])
  
@app.route('/search-citations', methods=['POST'])
def search_citations():
  pubs = [Publication.from_dict(serializer.loads(x)) for x in request.form.getlist('publication')]
  
  @delayed
  def get_results():
    with config.data_source() as conn:
      citing_pubs = list(conn.search_citations(pubs))
    
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
    
    autocit_count = 0
    autocit_count_by_index = {}
    
    filtered_pubs = []
    
    for pub in citing_pubs:
      if pub.autocit:
        autocit_count += 1
        for index in pub.indexes:
          if index.value not in autocit_count_by_index:
            autocit_count_by_index[index.value] = 1
          else:
            autocit_count_by_index[index.value] += 1
      else:
        filtered_pubs.append(pub)
    
    filtered_pubs.sort(key=get_first_author_surname)
    filtered_pubs.sort(key=lambda r: r.year)
    
    return SearchCitationsResult(filtered_pubs, autocit_count, autocit_count_by_index)
  
  return stream_template('search-citations.html', query_pubs=pubs, get_results=get_results)

if __name__ == '__main__':
  import sys

  if len(sys.argv) == 2 and sys.argv[1] == 'cherry':
    from cherrypy import wsgiserver
    d = wsgiserver.WSGIPathInfoDispatcher({'/': app})
    server = wsgiserver.CherryPyWSGIServer(('127.0.0.1', 5000), d)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
  else:
    app.run() # werkzeug
