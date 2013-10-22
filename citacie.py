import re

from flask import Flask
app = Flask(__name__)

from flask import render_template
from flask import request

from werkzeug.exceptions import BadRequest

import wok

data_sources = [wok.WOK()]

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
  for data_source in data_sources:
    with data_source as conn:
      results.extend(conn.search_by_author(surname, name=name, year=year))
  
  return render_template('search-by-author.html',
    search_name=name, search_surname=surname, search_year=year,
    results=results)

if __name__ == '__main__':
  import os
  if 'CITACIE_DEBUG' in os.environ:
    app.debug = True
  app.run()