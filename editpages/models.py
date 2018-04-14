from django.db import models
from utils import ModelMixin


class Item(ModelMixin, models.Model):
  page = models.CharField(max_length=200)
  key = models.CharField(max_length=200)
  note = models.ForeignKey('notepad.Note', models.SET_NULL, null=True, blank=True,
                           related_name='editpages_item')
  def __str__(self):
    content = self.note.content
    if len(content) > 66:
      content = content[:66]+'..'
    return '{!r}: {!r}'.format(self.key, self.note.content)


class List(ModelMixin, models.Model):
  title = models.ForeignKey('notepad.Note', models.SET_NULL, null=True, blank=True,
                            related_name='editpages_list')
  display_order = models.IntegerField()
  adding_visit = models.OneToOneField('traffic.Visit', models.SET_NULL, null=True, blank=True)
  deleted = models.BooleanField(default=False)
  deleting_visit = models.ForeignKey('traffic.Visit', models.SET_NULL, null=True, blank=True,
                                     related_name='deleted_list')


class ListItem(ModelMixin, models.Model):
  list = models.ForeignKey(List, models.SET_NULL, null=True, blank=True,
                           related_name='items')
  page = models.CharField(max_length=200)
  note = models.ForeignKey('notepad.Note', models.SET_NULL, null=True, blank=True,
                           related_name='editpages_listitem')
  display_order = models.IntegerField()
  adding_visit = models.OneToOneField('traffic.Visit', models.SET_NULL, null=True, blank=True)
  deleted = models.BooleanField(default=False)
  deleting_visit = models.ForeignKey('traffic.Visit', models.SET_NULL, null=True, blank=True,
                                     related_name='deleted_list')


class Move(ModelMixin, models.Model):
  """A record of an action that moves a List or ListItem.
  A movement either moves the object to a different display position or the ListItem to a different
  List."""
  type = models.CharField(max_length=127, choices=(('list','list'), ('position','position')))
  list = models.ForeignKey(List, models.SET_NULL, null=True, blank=True)
  list_item = models.ForeignKey(ListItem, models.SET_NULL, null=True, blank=True)
  old_display_order = models.IntegerField(null=True)
  new_display_order = models.IntegerField(null=True)
  old_list = models.ForeignKey(List, models.PROTECT, null=True, blank=True, related_name='moves_from')
  new_list = models.ForeignKey(List, models.PROTECT, null=True, blank=True, related_name='moves_to')
  visit = models.ForeignKey('traffic.Visit', models.PROTECT)
