from django.db import models
import http.client
import codecs
import logging
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


def http_request(host, path, secure=True, timeout=None, max_response=None):
  """A very quick and simple function for making an HTTP request.
  WARNING: This returns a str, so it does the bytes-to-str conversion. If a valid charset is in the
  Content-Type response header, it'll be fine, but if not it'll try utf-8, and if the decode fails,
  so will this."""
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
  except http.client.HTTPException:
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
