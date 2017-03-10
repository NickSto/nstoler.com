from django.db import models
from django.utils import timezone
import urllib.parse

# An actual person. Could include many visitors (different devices).
class User(models.Model):
  label = models.CharField(max_length=200)
  def __str__(self):
    return self.label

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

class Visit(models.Model):
  timestamp = models.DateTimeField(default=timezone.now)
  method = models.CharField(max_length=8)
  scheme = models.CharField(max_length=8)
  host = models.CharField(max_length=1023)
  path = models.CharField(max_length=4095)
  query_str = models.CharField(max_length=4095)
  referrer = models.URLField(max_length=4095, null=True, blank=True)
  visitor = models.ForeignKey(Visitor, models.PROTECT)
  def __str__(self):
    return '{}: {}'.format(self.timestamp, self.url)
  @property
  def url(self):
    url = urllib.parse.urlunparse((self.scheme, self.host, self.path, None, self.query_str, None))
    if url == '':
      return url
    elif self.scheme == '':
      return 'http:'+url
    else:
      return url

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
