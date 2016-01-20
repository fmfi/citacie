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

    def publications_from_query(self, query):
        url = 'https://api.elsevier.com/content/search/scopus'

        params = {
            'apiKey': self.api_key,
            'view': 'complete',
            'query': query
        }
        raw_json = requests.get(url, params=params).json()
        search_results = raw_json['search-results']
        total_results = int(search_results['opensearch:totalResults'])
        if total_results == 0:
            return

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

    def search_by_author(self, surname, name=None, year=None):
        query = 'authlastname({})'.format(surname)
        if name is not None:
            query += ' AND authfirst({})'.format(name)

        for pub in self.publications_from_query(query):
            yield pub

    def authors_from_json(self, json):
        def none_to_emptystr(s):
            if s is None:
                return ''
            return s

        return [Author(surname=author['surname'],
                       names=[none_to_emptystr(author['given-name'])])
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
                if type(d[key]) is list:
                    return [empty_to_none(x['$']) for x in d[key]]
                else:
                    return empty_to_none(d[key])
            else:
                return None

        def append_identifier(d, key, obj, type):
            ids = exists_to_none(d, key)
            if ids:
                if isinstance(ids, list):
                    for id in ids:
                        obj.identifiers.append(Identifier(id, type=type))
                else:
                    obj.identifiers.append(Identifier(ids, type=type))

        for entry in entries:
            author_count = int(entry['author-count']['$'])
            if author_count == 0:
                authors = []
            else:
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

    def search_citations_by_eid(self, eid):
        """Vrati iterator vracajuci zoznam publikacii, ktore cituju dane
        eid."""
        query = "refeid('{}')".format(eid)
        for pub in self.publications_from_query(query):
            yield pub

    def search_citations(self, publications):
        """Vrati iterator vracajuci zoznam publikacii, ktore cituju publikacie
           v zozname publications
        """
        for publication in publications:
            eid = list(Identifier.find_by_type(publication.identifiers,
                                               'SCOPUS'))
            if len(eid) == 0:
                continue
            eid = eid[0].value

            for pub in self.search_citations_by_eid(eid):
                yield pub

    def assign_indexes(self, publications):
        """Zisti a nastavi, v akych indexoch sa publikacie nachadzaju
        """
        pass

    def close(self):
        pass

if __name__ == '__main__':
    with ScopusWeb(api_key='').connect() as conn:
        pubs = list(conn.search_by_author('Vinar', name='T'))
        for pub in pubs:
            print pub
        print "Citations:"
        for pub in conn.search_citations(pubs):
            print pub
