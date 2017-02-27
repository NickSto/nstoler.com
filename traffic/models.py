from django.db import models
from django.utils import timezone

# Create your models here.
class Visitor(models.Model):
  cookie1 = models.CharField(max_length=16)
  cookie2 = models.CharField(max_length=24)
  ip = models.CharField(max_length=39)
  user_agent = models.CharField(max_length=200)
  is_me = models.BooleanField(default=False)
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
  page = models.TextField()
  referrer = models.TextField()
  visitor = models.ForeignKey(Visitor, models.PROTECT)
  def __str__(self):
    return '{}: {}'.format(self.timestamp, self.page)
