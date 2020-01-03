import functools
import logging
import requests
import smtplib
import threading
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

  @classmethod
  def get_default(cls, field_name):
    # Note: This is overly cautious because _meta is technically an internal API, but it turns out
    # Django essentially made it a public one: https://docs.djangoproject.com/en/1.8/ref/models/meta/
    if hasattr(cls, '_meta') and hasattr(cls._meta, 'get_field'):
      field = cls._meta.get_field(field_name)
      if hasattr(field, 'get_default'):
        return field.get_default()
    raise AttributeError('Interface for accessing field defaults has changed.')


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
  missing_keys = []
  for key in ('EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD'):
    if not (hasattr(settings, key) and getattr(settings, key)):
      missing_keys.append(key)
  if missing_keys:
    log.error(f'Failed sending email. Missing key(s) {", ".join(missing_keys)} in config file.')
    return False
  mails = 0
  try:
    mails = send_mail(subject, body, settings.EMAIL_HOST_USER, [settings.PERSONAL_EMAIL])
  except smtplib.SMTPException as error:
    log.error(
      f'Failed sending email from {settings.EMAIL_HOST_USER} to {settings.PERSONAL_EMAIL}: {error}'
    )
  return mails > 0
