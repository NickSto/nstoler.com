from django.db import models
from django.utils import timezone as utils_timezone
from utils import ModelMixin
import urllib.parse


class Cookie(ModelMixin, models.Model):
  direction = models.CharField(max_length=3, choices=(('set','set'), ('got','got')))
  name = models.CharField(max_length=4096)
  value = models.CharField(max_length=4096)
  max_age = models.IntegerField(null=True, blank=True)
  expires = models.DateTimeField(null=True, blank=True)
  path = models.CharField(max_length=1023)
  domain = models.CharField(max_length=127)
  secure = models.NullBooleanField()
  def __str__(self):
    return '{}: {}'.format(self.name, self.value)


# An actual person. Could include many visitors (different devices).
class User(ModelMixin, models.Model):
  label = models.CharField(max_length=200)
  def __str__(self):
    return self.label


class Visitor(ModelMixin, models.Model):
  ip = models.GenericIPAddressField()
  cookie1 = models.CharField(max_length=24, null=True, blank=True)
  cookie2 = models.CharField(max_length=24, null=True, blank=True)
  user_agent = models.CharField(max_length=200, null=True, blank=True)
  label = models.CharField(max_length=200)
  # Bot score:
  # positive = more sure it's a bot
  # negative = more sure it's not a bot
  # zero = not saying either way
  bot_score = models.IntegerField(default=0)
  user = models.ForeignKey(User, models.PROTECT)
  # Version:
  # Version 1: The cookies are the old, loosely-defined type.
  # Version 2: The cookies are strictly ones sent by the client.
  version = models.SmallIntegerField()
  def __str__(self):
    data = {'ip':self.ip, 'cookie':self.cookie1, 'user_agent':self.user_agent}
    data['label'] = ''
    if self.label:
      data['label'] = ' ({})'.format(self.label)
    return '{ip}{label} "{cookie}": {user_agent}'.format(**data)


class Visit(ModelMixin, models.Model):
  timestamp = models.DateTimeField(default=utils_timezone.now)
  method = models.CharField(max_length=8)
  scheme = models.CharField(max_length=8)
  host = models.CharField(max_length=1023)
  path = models.CharField(max_length=4095)
  query_str = models.CharField(max_length=4095)
  referrer = models.URLField(max_length=4095, null=True, blank=True)
  cookies_got = models.ManyToManyField(Cookie, related_name='visits_getting')
  cookies_set = models.ManyToManyField(Cookie, related_name='visits_setting')
  visitor = models.ForeignKey(Visitor, models.PROTECT)
  response = models.IntegerField(default=None, null=True, blank=True)
  location = models.URLField(max_length=4095, null=True, blank=True)
  def __str__(self):
    return '{}: {}'.format(self.timestamp, self.url)
  @property
  def url(self):
    url = urllib.parse.urlunparse((self.scheme, self.host, self.path, None, self.query_str, None))
    if url == '':
      return url
    elif self.scheme == '':
      return '????:'+url
    else:
      return url
  @url.setter
  def url(self, value):
    scheme, host, path, params, query_str, frag = urllib.parse.urlparse(value)
    self.scheme = scheme
    self.host = host
    self.path = path
    self.query_str = query_str
  def __repr__(self):
    class_name, args = self.generic_repr_bits(first_fields=('id', 'url'),
                                              skip_fields=('scheme', 'host', 'path', 'query_str'))
    args_strs = [key+'='+value for key, value in args if key is not None]
    return '{}({})'.format(class_name, ', '.join(args_strs))


# Since this data can change, there can be multiple entries for the same IP address, as it changes
# over time.
class IpInfo(ModelMixin, models.Model):
  ip = models.GenericIPAddressField(db_index=True)
  label = models.CharField(max_length=200)
  version = models.SmallIntegerField(null=True, blank=True, choices=((4,'4'), (6,'6')))
  asn = models.IntegerField(null=True, blank=True)
  isp = models.CharField(max_length=200)
  hostname = models.CharField(max_length=255)
  timezone = models.CharField(max_length=63)  # Long name like "America/Los_Angeles"
  latitude = models.FloatField(null=True, blank=True)
  longitude = models.FloatField(null=True, blank=True)
  country = models.CharField(max_length=63)
  region = models.CharField(max_length=127)
  town = models.CharField(max_length=127)
  zip = models.IntegerField(null=True, blank=True)
  timestamp = models.DateTimeField(default=utils_timezone.now)  # When this info was current.


# Types of visitors which should be considered robots.
class Robot(ModelMixin, models.Model):
  ip = models.GenericIPAddressField(null=True, blank=True)
  cookie1 = models.CharField(max_length=24, null=True, blank=True)
  cookie2 = models.CharField(max_length=24, null=True, blank=True)
  user_agent = models.CharField(max_length=200, null=True, blank=True, db_index=True)
  referrer = models.URLField(max_length=4095, null=True, blank=True, db_index=True)
  # Version 1: The cookies are the old, loosely-defined type.
  # Version 2: The cookies are strictly ones sent by the client.
  version = models.SmallIntegerField()
  def __str__(self):
    fields = []
    if self.ip:
      fields.append(self.ip)
    for cookie in (self.cookie1, self.cookie2):
      if cookie:
        fields.append('({})'.format(cookie))
    if self.user_agent:
      fields.append('"{}"'.format(self.user_agent))
    if self.referrer:
      fields.append('via: '+self.referrer)
    if len(fields) == 1:
      for value in (self.ip, self.cookie1, self.cookie2, self.user_agent):
        if value:
          return value
    return ' '.join(fields)
