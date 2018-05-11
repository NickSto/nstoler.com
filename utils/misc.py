import collections
import functools
import logging
import requests
import smtplib
import threading
import urllib.parse
from django.conf import settings
from django.core.mail import send_mail
from django.db import models
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
    self.invalid_value = False

  def parse(self, params_dict):
    """Convenience function to set all the parameters at once.
    Intended to be used like:
      query_params.parse(request.GET)"""
    for param_name, value in params_dict.items():
      self.set(param_name, value)

  def add(self, param_name, default=None, type=lambda x: x, min=None, max=None, choices=None):
    """Add a canonical parameter, set its default value and type.
    The type should be a callable. Incoming values will be passed through the callable before
    storing. If it throws a TypeError or ValueError, the default will be stored instead."""
    param = QueryParam(name=param_name, default=default, type=type, min=min, max=max, choices=choices)
    self.params[param_name] = param
    self[param_name] = default

  def set(self, param_name, value):
    """Set the value of a parameter.
    The value will be converted into the parameter's type.
    It doesn't have to be a canonical one. In that case, its order will be after all current
    canonical ones."""
    param = self.params.get(param_name, QueryParam(param_name))
    if param_name not in self.params:
      self.params[param_name] = param
    try:
      parsed_value = param.type(value)
    except (TypeError, ValueError):
      # If it's an invalid value, set it to be the default.
      parsed_value = param.default
      self.invalid_value = True
    if param.min is not None and parsed_value < param.min:
      parsed_value = param.min
      self.invalid_value = True
    if param.max is not None and parsed_value > param.max:
      parsed_value = param.max
      self.invalid_value = True
    if param.choices is not None and parsed_value not in param.choices:
      parsed_value = param.default
      self.invalid_value = True
    self[param_name] = parsed_value

  def but_with(self, *args, **kwargs):
    """Return a copy of the current object, but with the given parameter(s) set to the given value.
    Either give keyword arguments, or positional arguments with alternating parameter names & values.
    Usage:
      params.but_with(p=1, user='me')
      params.but_with('p', 1, 'user', 'me')
    """
    new_query_params = self.copy()
    for i in range(0, len(args), 2):
      if len(args) < i+2:
        break
      param_name = args[i]
      value = args[i+1]
      new_query_params.set(param_name, value)
    for param_name, value in kwargs.items():
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
      param = self.params.get(param_name, QueryParam(param_name))
      if value == param.default:
        continue
      param_name_quoted = urllib.parse.quote(param_name)
      value_quoted = urllib.parse.quote(str(value))
      components.append('{}={}'.format(param_name_quoted, value_quoted))
    if components:
      return '?'+'&'.join(components)
    else:
      return ''


class QueryParam(object):

  def __init__(self, name, default=None, type=lambda x: x, min=None, max=None, choices=None):
    self.name = name
    self.default = default
    self.type = type
    self.min = min
    self.max = max
    self.choices = choices

  def copy(self):
    return QueryParam(self.name, default=self.default, type=self.type, min=self.min, max=self.max)


def boolish(value):
  if value in (False, None, 0, '', 'False', 'false', '0'):
    return False
  elif value in (True, 1, 'True', 'true', '1'):
    return True
  else:
    raise ValueError('Invalid boolish value {!r}.'.format(value))


def recaptcha_verify(response_token, ip=None):
  # https://developers.google.com/recaptcha/docs/verify
  params = {
    'secret': settings.RECAPTCHA_SECRET,
    'response': response_token,
  }
  if ip:
    params['remoteip'] = ip
  try:
    response = http_request('https://www.google.com/recaptcha/api/siteverify', post_params=params,
                            timeout=4, json=True)
  except HttpError as error:
    log.error('Error making request to reCAPTCHA API ({}): {}'
              .format(error.type, error.message))
    return False
  if not response.get('success'):
    log.warning('reCAPTCHA came back invalid. Error codes: {!r}'
                .format(response.get('error-codes')))
    return False
  if not response.get('hostname') in settings.ALLOWED_HOSTS:
    log.warning('reCAPTCHA validated, but hostname is wrong. Saw {hostname!r}.'.format(**response))
    return False
  #TODO: Validate timestamp ('challenge_ts').
  return True


class HttpError(Exception):
  """A wrapper for all the things that can go wrong in http_request()."""
  def __init__(self, exception=None, error_type=None, message=None):
    self.exception = exception
    if self.exception is not None:
      self.type = type(exception).__name__
      self.message = str(exception)
    if error_type is not None:
      self.type = error_type
    if message is not None:
      self.message = message
    self.args = (self.message or '',)
  def __str__(self):
    output = type(self).__name__
    if self.type is not None:
      output += ' ('+self.type+')'
    if self.message is not None:
      output += ': '+self.message
    return output


def http_request(url, post_params=None, timeout=None, max_response=None, json=False):
  """A very quick and simple function for making an HTTP request.
  Returns the response as a str, unless `json` is True.
  On failure, raises an HttpError."""
  try:
    if post_params:
      response = requests.post(url, data=post_params, timeout=timeout)
    else:
      response = requests.get(url, timeout=timeout)
  except requests.exceptions.RequestException as error:
    raise HttpError(exception=error)
  if response.status_code != 200:
    raise HttpError(
      error_type='status_code',
      message='Error making request: response code {} ({}).'
              .format(response.status_code, response.reason)
    )
  if json:
    try:
      return response.json()
    except json.JSONDecodeError as error:
      raise HttpError(
        exception=error,
        message='Response not valid JSON: {!r}'.format(response.text)
      )
  else:
    return response.text


# From https://stackoverflow.com/questions/18420699/multithreading-for-python-django/28913218#28913218
def async(function):
  """Decorator to make a function execute in a background thread."""
  @functools.wraps(function)
  def wrapped_fxn(*args, **kwargs):
    t = threading.Thread(target=function, args=args, kwargs=kwargs)
    t.daemon = True
    t.start()
  return wrapped_fxn


def email_admin(subject, body):
  for key in ('EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD'):
    if not (hasattr(settings, key) and getattr(settings, key)):
      log.error('Failed sending email. Missing settings.{}.'.format(key))
      return False
  mails = 0
  try:
    mails = send_mail(subject, body, settings.EMAIL_HOST_USER, [settings.PERSONAL_EMAIL])
  except smtplib.SMTPException as error:
    log.error('Failed sending email to {}: {}'.format(settings.EMAIL_HOST_USER, error))
  return mails > 0
