# -*- coding: utf-8 -*-

def find_attributes(form_et, include_cb=None):
  attribs = []
  def append(name, value):
    attribs.append([name, value])
  for elem in form_et.findall(".//*"):
    if 'name' not in elem.attrib:
      continue
    name = elem.attrib['name']
    if elem.tag == '{http://www.w3.org/1999/xhtml}input':
      if 'type' in elem.attrib:
        typ = elem.attrib['type']
      else:
        typ = 'text'
      value = ''
      if 'value' in elem.attrib:
        value = elem.attrib['value']
      if typ == 'checkbox':
        if 'checked' in elem.attrib:
          append(name, value)
        elif include_cb and name in include_cb:
          append(name, value)
      elif typ in ('text', 'password', 'checkbox', 'textarea', 'hidden'):
        append(name, value)
    elif elem.tag == '{http://www.w3.org/1999/xhtml}select':
      value = None
      for option in elem.findall('.//{http://www.w3.org/1999/xhtml}option'):
        if 'value' in option.attrib:
          optval = option.attrib['value']
          if value == None:
            value = optval
          elif 'selected' in option.attrib:
            value = optval
      if value != None:
        append(name, value)
  return attribs