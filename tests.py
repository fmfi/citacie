#!/usr/bin/env python
# -*- coding: utf-8 -*-

from model import Author

author_parse_test_cases = [
  (u'Surname, First', Author(u'Surname', [u'First'])),
  (u'Surname, First Second', Author(u'Surname', [u'First', u'Second'])),
  (u'Smith JD', Author(u'Smith', [u'J.', u'D.'])),
  (u'Smith J.D.', Author(u'Smith', [u'J.', u'D.'])),
  (u'Smith, J.D.', Author(u'Smith', [u'J.', u'D.'])),
  (u'Smith J. D.', Author(u'Smith', [u'J.', u'D.'])),
  (u'Smith, J. D.', Author(u'Smith', [u'J.', u'D.'])),
  (u'Cheng Kai-Tei', Author(u'Cheng', [u'Kai', u'Tei'])),
  (u'Cheng K-T', Author(u'Cheng', [u'K.', u'T.'])),
  (u'Cheng K.-T.', Author(u'Cheng', [u'K.', u'T.'])),
  (u'Cheng K-T', Author(u'Cheng', [u'K.', u'T.'])),
  (u'Cheng K-T', Author(u'Cheng', [u'K.', u'T.'])),
  (u'Nobrega de Sousa, V.', Author(u'Nobrega de Sousa', [u'V.'])),
  (u'Nobrega de Sousa V.', Author(u'Nobrega de Sousa', [u'V.'])),
  (u'Nobrega de Sousa V', Author(u'Nobrega de Sousa', [u'V.'])),
  (u'Nobrega de Sousa V', Author(u'Nobrega de Sousa', [u'V.'])),
  (u'de Sousa V.', Author(u'de Sousa', [u'V.'])),
  (u'de Sousa Vito', Author(u'de Sousa', [u'Vito'])),
  (u'de Menezes Neto, R.', Author(u'de Menezes Neto', [u'R.'])),
  (u'de Menezes Neto R.', Author(u'de Menezes Neto', [u'R.'])),
  (u'McDonald R.', Author(u'McDonald', [u'R.'])),
]

author_short_name_test_cases = [
  (Author(u'MCDONALD', [u'R.']), u'McDonald, R.'),
  (Author(u'NOBREGA DE SOUSA', [u'V.']), u'Nobrega de Sousa, V.'),
]

def check_parsed_author(source, expected):
  parsed = Author.parse_sn_first(source)
  try:
    assert parsed.surname == expected.surname
    assert len(parsed.names) == len(expected.names)
    for i in range(len(parsed.names)):
      assert parsed.names[i] == expected.names[i], i
  except AssertionError:
    print "{!r} != {!r}".format(parsed, expected)
    raise

def test_parsing_author():
  for args in author_parse_test_cases:
    yield check_parsed_author, args[0], args[1]

def check_author_short_name(author, expected):
  short_name = author.short_name
  try:
    assert short_name == expected
  except AssertionError:
    print "{!r} != {!r}".format(short_name, expected)
    raise
  
def test_author_short_name():
  for args in author_short_name_test_cases:
    yield check_author_short_name, args[0], args[1]

if __name__ == "__main__":
  import nose
  nose.main()