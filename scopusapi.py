# -*- coding: utf-8 -*-
from data_source import DataSource, DataSourceConnection
from model import Publication, Author, Identifier, URL, Index
from htmlform import HTMLForm
from util import strip_bom, make_page_range
from throttle import ThreadingThrottler

from collections import OrderedDict
from urllib import urlencode, quote
import requests
from requests.utils import add_dict_to_cookiejar
import html5lib
from urlparse import urlparse, parse_qs
import re
import logging


class ScopusWeb(DataSource):
    def __init__(self, api_key):
        self.api_key = api_key

    def connect(self):
        return ScopusWebConnection(api_key=self.api_key)


class ScopusWebConnection(DataSourceConnection):
    def __init__(self, api_key):
        self.api_key = api_key

    def search_by_author(self, surname, name=None, year=None):
        url = 'https://api.elsevier.com/content/search/scopus'

        query = 'authlastname({})'.format(surname)
        if name is not None:
            query += ' AND authfirst({})'.format(name)

        params = {
            'apiKey': self.api_key,
            'view': 'complete',
            'query': query
        }
        raw_json = requests.get(url, params=params).json()
        entries = raw_json['search-results']['entry']
        for entry in entries:
            authors = []
            for author in entry['author']:
                authors.append(Author(surname=author['surname'],
                                      names=[author['given-name']]))
            year = int(entry['prism:coverDate'].split('-')[0])
            pub = Publication(entry['dc:title'], authors, year)
            pub.published_in = entry['prism:publicationName']
            pub.times_cited = entry['citedby-count']
            yield pub

    def search_citations(self, publications):
        """Vrati iterator vracajuci zoznam publikacii, ktore cituju publikacie
           v zozname publications
        """
        raise NotImplemented

    def assign_indexes(self, publications):
        """Zisti a nastavi, v akych indexoch sa publikacie nachadzaju
        """
        raise NotImplemented

    def assign_indexes(self, publications):
        """Zisti a nastavi, v akych indexoch sa publikacie nachadzaju
        """
        raise NotImplemented

    def close(self):
        pass

if __name__ == '__main__':
    with ScopusWeb(api_key='').connect() as conn:
        for pub in conn.search_by_author('Vinar', name='T'):
            print pub
