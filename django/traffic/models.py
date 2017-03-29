from django.db import models
from django.utils import timezone
import urllib.parse


class Cookie(models.Model):
  name = models.CharField(max_length=4096)
  value = models.CharField(max_length=4096)
  direction = models.CharField(max_length=3, choices=(('set','set'), ('got','got')))
  max_age = models.IntegerField(null=True, blank=True)
  expires = models.DateTimeField(null=True, blank=True)
  path = models.CharField(max_length=1023)
  domain = models.CharField(max_length=127)
  secure = models.NullBooleanField()
  def __str__(self):
    return '{}: {}'.format(self.name, self.value)
  def __repr__(self):
    fields = ('name', 'value', 'max_age', 'expires', 'path', 'domain', 'secure')
    class_name, args_str = generic_repr(self, fields)
    return '{}({})'.format(class_name, args_str)


# An actual person. Could include many visitors (different devices).
class User(models.Model):
  label = models.CharField(max_length=200)
  def __str__(self):
    return self.label
  def __repr__(self):
    class_name, args_str = generic_repr(self, ('id', 'label',))
    return '{}({})'.format(class_name, args_str)


class Visitor(models.Model):
  ip = models.GenericIPAddressField()
  cookie1 = models.CharField(max_length=24, null=True, blank=True)
  cookie2 = models.CharField(max_length=24, null=True, blank=True)
  user_agent = models.CharField(max_length=200, null=True, blank=True)
  label = models.CharField(max_length=200)
  user = models.ForeignKey(User, models.PROTECT)
  def __str__(self):
    data = {'ip':self.ip, 'cookie':self.cookie1, 'user_agent':self.user_agent}
    data['label'] = ''
    if self.label:
      data['label'] = ' ({})'.format(self.label)
    return '{ip}{label} "{cookie}": {user_agent}'.format(**data)
  def __repr__(self):
    class_name, args_str = generic_repr(self, ('ip', 'cookie1', 'cookie2', 'label', 'user_agent'))
    return '{}({})'.format(class_name, args_str)


class Visit(models.Model):
  timestamp = models.DateTimeField(default=timezone.now)
  method = models.CharField(max_length=8)
  scheme = models.CharField(max_length=8)
  host = models.CharField(max_length=1023)
  path = models.CharField(max_length=4095)
  query_str = models.CharField(max_length=4095)
  referrer = models.URLField(max_length=4095, null=True, blank=True)
  cookies_got = models.ManyToManyField(Cookie, related_name='visits_getting')
  cookies_set = models.ManyToManyField(Cookie, related_name='visits_setting')
  visitor = models.ForeignKey(Visitor, models.PROTECT)
  def __str__(self):
    return '{}: {}'.format(self.timestamp, self.url)
  def __repr__(self):
    class_name, args_str = generic_repr(self, ('timestamp', 'method', 'url', 'referrer'))
    return '{}({})'.format(class_name, args_str)
  @property
  def url(self):
    url = urllib.parse.urlunparse((self.scheme, self.host, self.path, None, self.query_str, None))
    if url == '':
      return url
    elif self.scheme == '':
      return 'http:'+url
    else:
      return url
  @url.setter
  def url(self, value):
    scheme, host, path, params, query_str, frag = urllib.parse.urlparse(value)
    self.scheme = scheme
    self.host = host
    self.path = path
    self.query_str = query_str


# Since this data can change, there can be multiple entries for the same IP address, as it changes
# over time.
class IpInfo(models.Model):
  ip = models.GenericIPAddressField(db_index=True)
  label = models.CharField(max_length=200)
  version = models.SmallIntegerField(choices=((4,'4'), (6,'6')))
  asn = models.IntegerField(null=True, blank=True)
  isp = models.CharField(max_length=200)
  latitude = models.FloatField(null=True, blank=True)
  longitude = models.FloatField(null=True, blank=True)
  country = models.CharField(max_length=63)
  region = models.CharField(max_length=127)
  town = models.CharField(max_length=127)
  zip = models.CharField(max_length=31)
  timestamp = models.DateTimeField(default=timezone.now)  # When this info was current.
  def __repr__(self):
    fields = ('ip', 'label', 'version', 'timestamp', 'asn', 'isp', 'latitude', 'longitude',
              'country', 'region', 'town', 'zip')
    class_name, args_str = generic_repr(self, fields)
    return '{}({})'.format(class_name, args_str)


def generic_repr(obj, attr_names):
  args = []
  for attr_name in attr_names:
    if hasattr(obj, attr_name):
      value = getattr(obj, attr_name)
      if value is not None and value != '':
        args.append('{}={!r}'.format(attr_name, value))
  class_name = type(obj).__name__
  return class_name, ', '.join(args)
