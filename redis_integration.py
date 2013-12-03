# -*- coding: utf-8 -*-
from data_source import DataSource, DataSourceConnection
from model import Publication
import redis
import hashlib
import json
import retools.lock

serializer = json

def hash_key(*args):
  s = serializer.dumps(args)
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
    self.data_key = '{}:{}:data'.format(self.namespace, self.key)
    self.lock_key = '{}:{}:lock'.format(self.namespace, self.key)
    self.locked = False
    self.lock = retools.lock.Lock(self.lock_key, expires=15*60, timeout=3*60, redis=redis)
  
  def __enter__(self):
    # najprv skusime, ci kluc existuje, ak hej, pouzijeme ho
    cached = self.redis.get(self.data_key)
    if cached != None:
      return cached
    self.lock.acquire()
    cached = self.redis.get(self.data_key)
    if cached != None:
      # uz niekto kluc vyrobil za nas
      self.lock.release()
      return cached
    self.locked = True
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

class RedisCachedDataSource(DataSource):
  def __init__(self, redis, key, real):
    self.redis = redis
    self.key = key
    self.real = real
    
  def connect(self):
    return RedisCachedConnection(self.redis, self, self.real)
  
class RedisCachedConnection(DataSourceConnection):
  def __init__(self, redis, ds, real):
    self.redis = redis
    self.ds = ds
    self.real = real
    self._real_conn = None
    self.namespace = 'citacie:cache:{}:search_by_author'.format(self.ds.key)
    self.cache = RedisCache(self.redis, self.namespace)
  
  @property
  def real_conn(self):
    if self._real_conn == None:
      self._real_conn = self.real.connect()
    return self._real_conn
  
  def search_by_author(self, surname, name=None, year=None):
    key = self.cache[hash_key(surname, name, year)]
    with key as cached_value:
      if cached_value != None:
        parsed_value = serializer.loads(cached_value)
        return [Publication.from_dict(x) for x in parsed_value]
      pubs = list(self.real_conn.search_by_author(surname, name=name, year=year))
      s = serializer.dumps([pub.to_dict() for pub in pubs])
      key.store(s)
      return pubs
  
  def search_citations(self, publications):
    return self.real_conn.search_citations(publications)
  
  def assign_indexes(self, publications):
    return self.real_conn.assign_indexes(publications)
  
  def close(self):
    if self._real_conn:
      self._real_conn.close()