# -*- coding: utf-8 -*-
import time
import threading
import logging

logger = logging.getLogger('citacie.throttle')

def max_or_none(seq):
  if len(seq) == 0:
    return None
  return max(seq)

class ThrottleInstance(object):
  def __init__(self, throttler, started_time=None):
    if started_time == None:
      started_time = time.time()
    self.started_time = started_time
    self.finished_time = None
    self.throttler = throttler
  
  def started_before(self, timestamp):
    return self.started_time < timestamp
  
  def finished_before(self, timestamp):
    if self.finished_time == None:
      return False
    return self.finished_time < timestamp
  
  def __enter__(self):
    pass
  
  def __exit__(self, type, value, traceback):
    self.throttler.finished(self)
    return False
  
  def __repr__(self):
    return 'ThrottleInstance({}, {})'.format(self.started_time, self.finished_time)
  
  def __str__(self):
    return repr(self)

class ThreadingThrottler(object):
  def __init__(self, number, period, min_delay=0, finished_delay=0, period_delay=0, timeout=None, sleep=None):
    """
    number - pocet requestov
    period - za aku dobu (v sekundach)
    min_delay - kolko minimalne cakat medzi zaciatkami requestov (v sekundach)
    period_delay - kolko cakat po skonceni periody (v sekundach)
    finished_delay - kolko cakat po skonceni requestu
    timeout - kolko maximalne cakat nez sa podari ziskat zdroj
    """
    self.number = number
    self.period = period
    self.min_delay = min_delay
    self.finished_delay = finished_delay
    self.period_delay = period_delay
    self.timeout = timeout
    self.history = [] # pole timestampov
    if sleep == None:
      def minsleep(sec):
        return time.sleep(max(0.1, sec))
      sleep = minsleep
    self._sleep = sleep
    self._lock = threading.Lock()
  
  def throttle(self):
    wait_until = None
    if self.timeout:
      deadline = time.time() + self.timeout
    else:
      deadline = None
    timed_out = True
    result = None
    while deadline == None or time.time() < deadline:
      if wait_until:
        if wait_until > deadline:
          break
        delay = wait_until - time.time()
        logger.debug('calculated delay %f', delay)
        if delay > 0:
          logger.debug('throttle sleep for %f seconds', delay)
          self._sleep(delay)
        wait_until = None
      with self._lock:
        now = time.time()
        
        # zahodime staru historiu
        while len(self.history) > 0 and self.history[0].started_before(now - self.period):
          logger.debug('popping history item from %f', self.history[0].started_time)
          self.history.pop(0)
        
        max_finished = max_or_none([x.finished_time for x in self.history if x != None])
        max_started = max_or_none([x.started_time for x in self.history if x != None])
        
        if len(self.history) == self.number:
          min_started = self.history[0].started_time
          # musime pockat do skoncenia periody
          wait_until = max(min_started + self.period + self.period_delay, max_started + self.min_delay)
          if max_finished:
            wait_until = max(wait_until, max_finished + self.finished_delay)
          logger.debug('period used %s, waiting until %f', str(self.history), wait_until)
          continue
        
        # kolko treba pockat medzi requestami
        if len(self.history):
          wait_until = max_started + self.min_delay
          if max_finished:
            wait_until = max(wait_until, max_finished + self.finished_delay)
          our_request = max(wait_until, now)
        else:
          wait_until = None
          our_request = now
        
        result = ThrottleInstance(self, our_request)
        self.history.append(result)
        logger.debug('adding to history %f', our_request)
        timed_out = False
        break
    if timed_out:
      raise ThrottleTimeout()
    if wait_until:
      delay = wait_until - time.time()
      if delay > 0:
        logger.debug('throttle final sleep for %f seconds', delay)
        self._sleep(delay)
      wait_until = None
    logger.debug('throttle finished')
    return result
  
  def finished(self, inst):
    with self._lock:
      inst.finished_time = time.time()
  
  def __call__(self):
    return self.throttle()

class ThrottleTimeout(BaseException):
  """Vyhodene ked sa po dlhy cas nepodari ziskat throttle zamok"""

if __name__ == '__main__':
  logger.setLevel(logging.DEBUG)
  handler = logging.StreamHandler()
  handler.setLevel(logging.DEBUG)
  logger.addHandler(handler)
  t = ThreadingThrottler(2, 10, timeout=20)
  for i in range(5):
    with t():
      pass