from django.db import models
from utils import ModelMixin

class Page(ModelMixin, models.Model):
  name = models.CharField(max_length=200)
  def __str__(self):
    return self.name

class Note(ModelMixin, models.Model):
  page = models.ForeignKey(Page, models.SET_NULL, null=True, blank=True)
  content = models.TextField()
  visit = models.OneToOneField('traffic.Visit', models.SET_NULL, null=True, blank=True)
  protected = models.BooleanField(default=False)  # Only admin can delete.
  deleted = models.BooleanField(default=False)
  deleting_visit = models.ForeignKey('traffic.Visit', models.SET_NULL, null=True, blank=True,
                                     related_name='deleted_note')
  def __str__(self):
    deleted = ''
    if self.deleted:
      deleted = ' (deleted)'
    return '{}{}: {}'.format(self.page, deleted, repr(self.content[:50]))
