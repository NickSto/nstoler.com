from django.db import models
import codecs
import collections
import functools
import http.client
import logging
import socket
import threading
import urllib.parse
log = logging.getLogger(__name__)


class ModelMixin(object):

  def __repr__(self):
    class_name, args = self.generic_repr_bits()
    args_strs = [key+'='+value for key, value in args if key is not None]
    return '{}({})'.format(class_name, ', '.join(args_strs))

  def generic_repr_bits(self, first_fields=(), skip_fields=()):
    args = []
    for name in first_fields:
      args.append(self.generic_repr_format(name))
    for field in self._meta.fields:
      if type(field) is models.ForeignKey:
        continue
      name = field.name
      if name not in first_fields and name not in skip_fields:
        args.append(self.generic_repr_format(name))
    class_name = type(self).__name__
    return class_name, args

  def generic_repr_format(self, name, max_len=100):
    if hasattr(self, name):
      value = getattr(self, name)
      if value is not None and value != '':
        value_str = repr(value)
        if len(value_str) > max_len:
          if isinstance(value, str):
            value_str = repr(value[:max_len-5]+'...')
          else:
            # It's hard to truncate an arbitrary repr string. Let's just make a little effort to close
            # any opening quote marks.
            value_str = repr(value_str[:max_len-5]+'...')
        return name, value_str
    return None, None


class QueryParams(collections.OrderedDict):
  """A class to simplify handling query parameters and enable simpler query strings.
  This encapsulates parsing the values of query strings, holding their values, and producing
  altered query strings in a simplified format.
  It works by first declaring the accepted ("canonical") query string parameters with add().
  This object retains information on the preferred order of parameters, along with their default
  values and type.
  Then, you give parse() the parameters given by the user, and it will interpret the values
  according to their expected type.
  Then, you can continue using this object as a dict holding the parameter values, and getting and
  setting them as you wish.
  Finally, you can produce query strings by giving this object to str(). The query strings will list
  the parameters in the preferred order, omitting parameters with the default values."""

  def __init__(self):
    self.params = collections.OrderedDict()

  def parse(self, params_dict):
    """Convenience function to set all the parameters at once.
    Intended to be used like:
      query_params.parse(request.GET)"""
    for param_name, value in params_dict.items():
      self.set(param_name, value)

  def add(self, param_name, default=None, type=lambda x: x):
    """Add a canonical parameter, set its default value and type.
    The type should be a callable. Incoming values will be passed through the callable before
    storing. If it throws a TypeError or ValueError, the default will be stored instead."""
    self.params[param_name] = {'default':default, 'type':type}
    self[param_name] = default

  def set(self, param_name, value):
    """Set the value of a parameter.
    The value will be converted into the parameter's type.
    It doesn't have to be a canonical one. In that case, its order will be after all current
    canonical ones."""
    param = self.params.get(param_name, {})
    if param_name not in self.params:
      self.params[param_name] = param
    param_type = param.get('type', lambda x: x)
    try:
      parsed_value = param_type(value)
    except (TypeError, ValueError):
      # If it's an invalid value, set it to be the default.
      parsed_value = param.get('default', None)
    self[param_name] = parsed_value

  def but_with(self, param_name, value):
    """Return a copy of the current object, but with the given parameter set to the given value."""
    new_query_params = self.copy()
    new_query_params.set(param_name, value)
    return new_query_params

  def copy(self):
    copy = super().copy()
    copy.params = collections.OrderedDict()
    for param_name, param in self.params.items():
      copy.params[param_name] = param.copy()
    return copy

  def __str__(self):
    """Return a query string with the parameters set to their current values.
    Preserves the canonical order of the parameters, and omits any whose current value is the default.
    """
    components = []
    for param_name, value in self.items():
      param = self.params.get(param_name, {})
      if value == param.get('default', None):
        continue
      param_name_quoted = urllib.parse.quote(param_name)
      value_quoted = urllib.parse.quote(str(value))
      components.append('{}={}'.format(param_name_quoted, value_quoted))
    if components:
      return '?'+'&'.join(components)
    else:
      return ''


def boolish(value):
  if value in (False, None, 0, '', 'False', 'false', '0'):
    return False
  elif value in (True, 1, 'True', 'true', '1'):
    return True
  else:
    raise ValueError('Invalid boolish value {!r}.'.format(value))


def http_request(host, path, secure=True, timeout=None, max_response=None):
  """A very quick and simple function for making an HTTP request.
  Returns the response as a str.
  On failure, returns None.
  WARNING: This returns a str, so it does the bytes-to-str conversion. If a valid charset is in the
  Content-Type response header, it'll be fine, but if not it'll try utf-8, and if the decode fails,
  so will this (and it'll return None)."""
  if secure:
    conex_class = http.client.HTTPSConnection
  else:
    conex_class = http.client.HTTPConnection
  try:
    if timeout is None:
      conex = conex_class(host)
    else:
      conex = conex_class(host, timeout=timeout)
    conex.request('GET', path)
    response = conex.getresponse()
    if response.status != 200:
      if secure:
        url = 'https://'+host+path
      else:
        url = 'http://'+host+path
      log.warning('Received response {} from {}'.format(response.status, url))
      conex.close()
      return None
    if max_response is None:
      response_bytes = response.read()
    else:
      response_bytes = response.read(max_response)
    content_type = response.headers.get('Content-Type')
    encoding = get_encoding(content_type)
    if encoding:
      response_str = str(response_bytes, encoding)
    else:
      try:
        response_str = str(response_bytes, 'utf8')
      except UnicodeError:
        return None
    conex.close()
    return response_str
  except (http.client.HTTPException, socket.error):
    return None


def get_encoding(content_type):
  if not content_type:
    return None
  fields = content_type.split(';')
  if len(fields) != 2:
    return None
  mime_encoding = fields[1]
  fields = mime_encoding.split('=')
  if len(fields) != 2:
    return None
  key, encoding = fields
  if key.strip().lower() != 'charset':
    return None
  encoding = encoding.strip().lower()
  try:
    codecs.getencoder(encoding)
    return encoding
  except LookupError:
    return None


# From https://stackoverflow.com/questions/18420699/multithreading-for-python-django/28913218#28913218
def async(function):
  """Decorator to make a function execute in a background thread."""
  @functools.wraps(function)
  def wrapped_fxn(*args, **kwargs):
    t = threading.Thread(target=function, args=args, kwargs=kwargs)
    t.daemon = True
    t.start()
  return wrapped_fxn
