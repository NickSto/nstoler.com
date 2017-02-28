from django.db import models
from django.utils import timezone

class Visitor(models.Model):
  ip = models.GenericIPAddressField()
  cookie1 = models.CharField(max_length=16, null=True, blank=True)
  cookie2 = models.CharField(max_length=24, null=True, blank=True)
  user_agent = models.CharField(max_length=200, null=True, blank=True)
  is_me = models.NullBooleanField(default=None, null=True, blank=True)
  label = models.CharField(max_length=200)
  def __str__(self):
    data = {'ip':self.ip, 'cookie':self.cookie1, 'user_agent':self.user_agent}
    data['is_me'] = ''
    if self.is_me:
      data['is_me'] = ' (me)'
    data['label'] = ''
    if self.label:
      data['label'] = ' ({})'.format(self.label)
    return '{ip}{is_me}{label} "{cookie}": {user_agent}'.format(**data)

class Visit(models.Model):
  timestamp = models.DateTimeField(default=timezone.now)
  method = models.CharField(max_length=8)
  host = models.CharField(max_length=1023)
  url = models.URLField(max_length=4095)
  referrer = models.URLField(max_length=4095, null=True, blank=True)
  visitor = models.ForeignKey(Visitor, models.PROTECT)
  def __str__(self):
    return '{}: {}'.format(self.timestamp, self.url)
