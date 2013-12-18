# -*- coding: utf-8 -*-

class HTMLInput(object):
  def __init__(self, name, value):
    self.name = name
    self.value = value
  
  def to_params(self):
    return [(self.name, self.value)]

class HTMLCheckbox(HTMLInput):
  def __init__(self, name, value, checked=False):
    super(HTMLCheckbox, self).__init__(name, value)
    self.checked = checked
  
  def to_params(self):
    if not self.checked:
      return []
    return super(HTMLCheckbox, self).to_params()

class HTMLForm(object):
  def __init__(self, form_et):
    self.action = form_et.attrib.get('action', None)
    self.method = form_et.attrib.get('method', None)
    self.inputs = []
    
    def append(name, value):
      self.inputs.append(HTMLInput(name, value))
    
    for elem in form_et.getiterator():
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
          self.inputs.append(HTMLCheckbox(name, value, checked=('checked' in elem.attrib)))
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
    
  def set_value(self, name, value):
    try:
      inp = self[name]
      inp.value = value
    except KeyError:
      self.inputs.append(HTMLInput(name, value))
  
  def check_all(self, name):
    for inp in self.inputs:
      if inp.name == name:
        inp.checked = True
  
  def __getitem__(self, name):
    for inp in self.inputs:
      if inp.name == name:
        return inp
    raise KeyError(name)
  
  def to_params(self):
    params = []
    for inp in self.inputs:
      params.extend(inp.to_params())
    return params