from django.db import models
from django.utils import timezone

# Create your models here.
class Note(models.Model):
  page = models.CharField(max_length=200)
  content = models.TextField()
  visit = models.ForeignKey('traffic.Visit', models.SET_NULL, null=True, blank=True)
  def __str__(self):
    return '{}: {}'.format(self.page, repr(self.content[:50]))
