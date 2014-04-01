# -*- coding: utf-8 -*-
from data_source import DataSource, DataSourceConnection
from wok import WokWS, WokWSConnection, WokWeb, WokWebConnection
from scopus import ScopusWeb, ScopusWebConnection
from model import Publication
import redis
import hashlib
import json
import retools.lock
import time

serializer = json

def dumps(arg):
  return serializer.dumps(arg, sort_keys=True)

def loads(arg):
  return serializer.loads(arg)

def hash_key(*args):
  s = dumps(args)
  return hashlib.sha1(s).hexdigest()

class RedisCache(object):
  def __init__(self, redis, namespace):
    self.redis = redis
    self.namespace = namespace
  
  def __getitem__(self, key):
    return RedisCacheKey(self.redis, self.namespace, key)

class RedisCacheKey(object):
  def __init__(self, redis, namespace, key):
    self.redis = redis
    self.namespace = namespace
    self.key = key
    self.namespace_keys = '{}:keys'.format(self.namespace)
    self.misses_key = '{}:misses'.format(self.namespace)
    self.hits_key = '{}:hits'.format(self.namespace)
    self.data_key = '{}:{}:data'.format(self.namespace, self.key)
    self.lock_key = '{}:{}:lock'.format(self.namespace, self.key)
    self.locked = False
    self.lock = retools.lock.Lock(self.lock_key, expires=15*60, timeout=3*60, redis=redis)
  
  def _hit(self):
    self.redis.incr(self.hits_key)
  
  def _missed(self):
    self.redis.incr(self.misses_key)
  
  def __enter__(self):
    # najprv skusime, ci kluc existuje, ak hej, pouzijeme ho
    cached = self.redis.get(self.data_key)
    if cached != None:
      self._hit()
      return cached
    self.lock.acquire()
    cached = self.redis.get(self.data_key)
    if cached != None:
      # uz niekto kluc vyrobil za nas
      self.lock.release()
      self._hit()
      return cached
    self.locked = True
    self._missed()
    return None
  
  def __exit__(self, type, value, traceback):
    if self.locked:
      self.lock.release()
    return False
  
  def store(self, s, expires=60*60):
    pl = self.redis.pipeline()
    pl.set(self.data_key, s)
    pl.expire(self.data_key, expires)
    pl.sadd(self.namespace_keys, self.key)
    pl.execute()

class RedisWrappedDataSource(DataSource):
  def __init__(self, redis, key, real):
    self.redis = redis
    self.key = key
    self.real = real

class RedisCachedDataSource(RedisWrappedDataSource):
  def connect(self):
    return RedisCachedConnection(self.redis, self, self.real)
  
class RedisCachedConnection(DataSourceConnection):
  def __init__(self, redis, ds, real):
    self.redis = redis
    self.ds = ds
    self.real = real
    self._real_conn = None
    self.namespace = 'citacie:cache:{}'.format(self.ds.key)
    self.cache_search_by_author = RedisCache(self.redis, '{}:search_by_author'.format(self.namespace))
    self.cache_search_citations = RedisCache(self.redis, '{}:search_citations'.format(self.namespace))
  
  @property
  def real_conn(self):
    if self._real_conn == None:
      self._real_conn = self.real.connect()
    return self._real_conn
  
  def search_by_author(self, surname, name=None, year=None):
    key = self.cache_search_by_author[hash_key(surname, name, year)]
    with key as cached_value:
      if cached_value != None:
        parsed_value = loads(cached_value)
        for pub_dict in parsed_value:
          yield Publication.from_dict(pub_dict)
        return
      pubs = []
      for pub in self.real_conn.search_by_author(surname, name=name, year=year):
        yield pub
        pubs.append(pub)
      s = dumps([pub.to_dict() for pub in pubs])
      key.store(s)
  
  def search_citations(self, publications):
    key = self.cache_search_citations[hash_key([[pub.to_dict() for pub in publications]])]
    with key as cached_value:
      if cached_value != None:
        parsed_value = loads(cached_value)
        for pub_dict in parsed_value:
          yield Publication.from_dict(pub_dict)
        return
      pubs = []
      for pub in self.real_conn.search_citations(publications):
        yield pub
        pubs.append(pub)
      s = dumps([pub.to_dict() for pub in pubs])
      key.store(s)
  
  def assign_indexes(self, publications):
    return self.real_conn.assign_indexes(publications)
  
  def close(self):
    if self._real_conn:
      self._real_conn.close()

class RequestLogger(object):
  def __init__(self, redis, namespace):
    self.redis = redis
    self.namespace = namespace
  
  def log(self, method, key_data, value):
    key = hash_key(*key_data)
    method_ns = '{}:{}'.format(self.namespace, method)
    fqkey = '{}:{}:data'.format(method_ns, key)
    fqkey_params = '{}:{}:params'.format(method_ns, key)
    pl = self.redis.pipeline()
    pl.set(fqkey, value)
    pl.set(fqkey_params, dumps(key_data))
    pl.zadd(method_ns, time.time(), key)
    pl.execute()

class RedisLogDataSource(RedisWrappedDataSource):
  def connect(self):
    return RedisLogConnection(self.redis, self, self.real.connect())

class RedisLogConnection(DataSourceConnection):
  def __init__(self, redis, ds, real_conn):
    self.real_conn = real_conn
    self.ds = ds
    self.rl = RequestLogger(redis, 'citacie:log:request:{}'.format(self.ds.key))
  
  def search_by_author(self, surname, name=None, year=None):
    pubs = []
    for pub in self.real_conn.search_by_author(surname, name=name, year=year):
      yield pub
      pubs.append(pub)
    self.rl.log('search_by_author', [surname, name, year], dumps([pub.to_dict() for pub in pubs]))
  
  def search_citations(self, publications):
    cits = []
    for cit in self.real_conn.search_citations(publications):
      yield cit
      cits.append(cit)
    self.rl.log('search_citations', [[pub.to_dict() for pub in publications]], dumps([cit.to_dict() for cit in cits]))
  
  def assign_indexes(self, publications):
    return self.real_conn.assign_indexes(publications)
  
  def close(self):
    self.real_conn.close()

class RedisLogWokWS(WokWS):
  def __init__(self, redis=None, key=None, *args, **kwargs):
    self.redis = redis
    self.key = key
    super(RedisLogWokWS, self).__init__(*args, **kwargs)
  
  def connect(self):
    return RedisLogWokWSConnection(self.redis, self.key, self.throttler, self.auth)

class RedisLogWokWSConnection(WokWSConnection):
  def __init__(self, redis, key, *args, **kwargs):
    self.rl = RequestLogger(redis, 'citacie:log:request:{}'.format(key))
    super(RedisLogWokWSConnection, self).__init__(*args, **kwargs)
  
  def _log_search(self, context, records):
    if context is None:
      return
    self.rl.log(context[0], context[1:], str(records))

class RedisLogWokWeb(WokWeb):
  def __init__(self, redis=None, key=None, *args, **kwargs):
    self.redis = redis
    self.key = key
    super(RedisLogWokWeb, self).__init__(*args, **kwargs)
  
  def connect(self):
    return RedisLogWokWebConnection(self.redis, self.key, self.url, self.throttler, additional_headers=self.additional_headers)

class RedisLogWokWebConnection(WokWebConnection):
  def __init__(self, redis, key, *args, **kwargs):
    self.rl = RequestLogger(redis, 'citacie:log:request:{}'.format(key))
    super(RedisLogWokWebConnection, self).__init__(*args, **kwargs)
  
  def _log_tab_delimited(self, cite_url, origin_ut, text):
    self.rl.log('_get_citations_from_url', [origin_ut], text)

class RedisLogScopusWeb(ScopusWeb):
  def __init__(self, redis, key, *args, **kwargs):
    self.redis = redis
    self.key = key
    super(RedisLogScopusWeb, self).__init__(*args, **kwargs)
  
  def connect(self):
    return RedisLogScopusWebConnection(self.redis, self.key, self.throttler, additional_headers=self.additional_headers, proxies=self.proxies)

class RedisLogScopusWebConnection(ScopusWebConnection):
  def __init__(self, redis, key, *args, **kwargs):
    self.rl = RequestLogger(redis, 'citacie:log:request:{}'.format(key))
    super(RedisLogScopusWebConnection, self).__init__(*args, **kwargs)
  
  def _log_csv(self, context, content, encoding='UTF-8'):
    if context is None:
      return
    self.rl.log(context[0], context[1:], content)
