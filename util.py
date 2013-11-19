# -*- coding: utf-8 -*-
import codecs
import unicodedata
import string


def strip_bom(bytestr):
  if bytestr.startswith(codecs.BOM_UTF8):
    return bytestr[len(codecs.BOM_UTF8):]
  return bytestr

def make_page_range(begin_page, end_page):
  page_range = []
  if begin_page:
    page_range.append(begin_page)
  if end_page:
    page_range.append(end_page)
  if len(page_range) == 0:
    return None
  return u'-'.join(page_range)

def normalize(unicode_string):
  if unicode_string == None:
    return None
  if not isinstance(unicode_string, unicode):
    unicode_string = unicode_string.decode('UTF-8')
  return ''.join(x for x in unicodedata.normalize('NFKD', unicode_string) if x in string.ascii_letters).lower()
