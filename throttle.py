# -*- coding: utf-8 -*-
import time
import threading

class ThrottleInstance(object):
  def __init__(self, started_time=None):
    if started_time == None:
      started_time = time.time()
    self.started_time = started_time
    self.finished_time = None
  
  def started_before(self, timestamp):
    return self.started_time < timestamp
  
  def finished_before(self, timestamp):
    if self.finished_time == None:
      return False
    return self.finished_time < timestamp

class ThreadingThrottler(object):
  def __init__(self, number, period, min_delay=0, period_delay=0, timeout=None, sleep=None):
    """
    number - pocet requestov
    period - za aku dobu (v sekundach)
    min_delay - kolko minimalne cakat medzi requestami (v sekundach)
    period_delay - kolko cakat po skonceni periody (v sekundach)
    timeout - kolko maximalne cakat nez sa podari ziskat zdroj
    """
    self.number = number
    self.period = period
    self.min_delay = min_delay
    self.period_delay = period_delay
    self.timeout = timeout
    self.history = [] # pole timestampov
    if sleep == None:
      sleep = time.sleep
    self._sleep = sleep
    self._lock = threading.Lock()
  
  def throttle(self):
    wait_until = None
    if self.timeout:
      deadline = time.time() + self.timeout
    else:
      deadline = None
    timed_out = True
    while deadline == None or time.time() < deadline:
      if wait_until:
        if wait_until > deadline:
          break
        delay = time.time() - wait_until
        if delay > 0:
          self._sleep(delay)
        wait_until = None
      with self._lock:
        now = time.time()
        
        # zahodime staru historiu
        while len(self.history) > 0 and self.history[0].started_before(now - self.period):
          self.history.pop(0)
        
        if len(self.history) == self.number:
          # musime pockat do skoncenia periody
          wait_until = max(self.history[0].started_time + self.period + self.period_delay, self.history[-1].started_time + self.min_delay)
          continue
        
        # kolko treba pockat medzi requestami
        if len(self.history):
          wait_until = self.history[-1].started_time + self.min_delay
          our_request = max(wait_until, now)
        else:
          wait_until = None
          our_request = now
        
        self.history.append(ThrottleInstance(our_request))
        timed_out = False
        break
    if timed_out:
      raise ThrottleTimeout()
    if wait_until:
      delay = time.time() - wait_until
      if delay > 0:
        self._sleep(delay)
      wait_until = None
  
  def __enter__(self):
    self.throttle()
  
  def __exit__(self, type, value, traceback):
    return False

class ThrottleTimeout(BaseException):
  """Vyhodene ked sa po dlhy cas nepodari ziskat throttle zamok"""