# -*- coding: utf-8 -*-
import codecs

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