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
import re

INCLUDING_RE = r' \(including subseries [^)]+\)'


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
        for pub in self.entries_to_publications(entries):
            yield pub

        def find_next_url(links):
            for link in links:
                if link['@ref'] == 'next':
                    return link['@href']
            return None

        while True:
            next_link = find_next_url(raw_json['search-results']['link'])
            if next_link is None:
                break
            raw_json = requests.get(next_link).json()
            entries = raw_json['search-results']['entry']
            for pub in self.entries_to_publications(entries):
                yield pub

    def authors_from_json(self, json):
        return [Author(surname=author['surname'], names=[author['given-name']])
                for author in json]

    def entries_to_publications(self, entries):
        """Prerobi data zo SCOPUS json reprezentacie na internu Publication."""

        def empty_to_none(s):
            if s is None:
                return None
            s = s.strip()
            if len(s) == 0:
                return None
            return s

        def exists_to_none(d, key):
            if key in d:
                return empty_to_none(d[key])
            else:
                return None

        def append_identifier(d, key, obj, type):
            id = exists_to_none(d, key)
            if id:
                obj.identifiers.append(Identifier(id, type=type))

        for entry in entries:
            authors = self.authors_from_json(entry['author'])
            year = empty_to_none(entry['prism:coverDate'])
            if year:
                year = int(year.split('-')[0])
            pub = Publication(empty_to_none(entry['dc:title']), authors, year)
            pub.times_cited = empty_to_none(entry['citedby-count'])

            source_title = empty_to_none(entry['prism:publicationName'])
            if source_title:
                source_title, replacements = re.subn(INCLUDING_RE,
                                                     '',
                                                     source_title)
                source_title = source_title.strip()
                if replacements:
                    pub.series = source_title
                else:
                    pub.published_in = source_title

            pub.pages = exists_to_none(entry, 'prism:pageRange')
            pub.volume = exists_to_none(entry, 'prism:volume')
            pub.issue = exists_to_none(entry, 'prism:issueIdentifier')
            pub.pages = exists_to_none(entry, 'prism:pageRange')

            append_identifier(entry, 'prism:doi', pub, 'DOI')
            append_identifier(entry, 'prism:isbn', pub, 'ISBN')
            append_identifier(entry, 'prism:issn', pub, 'ISSN')
            append_identifier(entry, 'eid', pub, 'SCOPUS')

            pub.indexes.append(Index('SCOPUS', type='SCOPUS'))

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
