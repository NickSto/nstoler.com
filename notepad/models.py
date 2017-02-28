from django.db import models
from django.utils import timezone

class Note(models.Model):
  page = models.CharField(max_length=200)
  content = models.TextField()
  deleted = models.BooleanField(default=False)
  visit = models.ForeignKey('traffic.Visit', models.SET_NULL, null=True, blank=True)
  def __str__(self):
    deleted = ''
    if self.deleted:
      deleted = ' (deleted)'
    return '{}{}: {}'.format(self.page, deleted, repr(self.content[:50]))
