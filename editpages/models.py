import json
from django.template.defaultfilters import escape
from django.db import models
from utils import ModelMixin
from notepad.models import Note
from traffic.models import Visit
from .templatetags.markdown import parse_markdown


#TODO: Make Item and ListItem inherint from an abstract base class?
#      https://godjango.com/blog/django-abstract-base-class-model-inheritance/


class Item(ModelMixin, models.Model):
  type = 'item'
  page = models.CharField(max_length=200)
  key = models.CharField(max_length=200)
  attributes = models.ForeignKey(Note, models.SET_NULL, null=True, blank=True,
                                 related_name='attr_item')  # JSON-encoded key/values.
  note = models.ForeignKey(Note, models.SET_NULL, null=True, blank=True, related_name='editpages_item')
  def content(self):
    if self.note:
      return self.note.content
    else:
      return ''
  def mcontent(self):
    return parse_markdown(escape(self.content()))
  def title(self):
    if not self.note:
      return ''
    for line in self.note.content.splitlines():
      if line.startswith('#'):
        return line.lstrip('#').strip()
    return ''
  def mtitle(self):
    return parse_markdown(escape(self.title()))
  def body(self):
    if not self.note:
      return ''
    # Ignore leading blank lines.
    started = False
    output_lines = []
    for line in self.note.content.splitlines():
      if started:
        output_lines.append(line)
      elif line:
        started = True
        if not line.startswith('#'):
          output_lines.append(line)
    return '\n'.join(output_lines)
  def mbody(self):
    return parse_markdown(escape(self.body()))
  def jattrs(self):
    if self.attributes:
      try:
        data = json.loads(self.attributes.content)
      except json.JSONDecodeError:
        return {}
      if isinstance(data, dict):
        return data
      else:
        return {}
    else:
      return {}
  def __str__(self):
    content = self.note.content
    if len(content) > 66:
      content = content[:66]+'..'
    return '{!r}: {!r}'.format(self.key, self.note.content)


class ListItem(Item):
  type = 'listitem'
  parent = models.ForeignKey('self', models.SET_NULL, null=True, blank=True, related_name='items')
  display_order = models.IntegerField()
  adding_visit = models.OneToOneField(Visit, models.SET_NULL, null=True, blank=True,
                                      related_name='added_listitem')
  deleted = models.BooleanField(default=False)
  deleting_visit = models.ForeignKey(Visit, models.SET_NULL, null=True, blank=True,
                                     related_name='deleted_listitem')
  def sorted_items(self):
    return self.items.order_by('display_order', 'id')


class Move(ModelMixin, models.Model):
  """A record of an action that moves a List or ListItem.
  A movement either moves the object to a different display position or the ListItem to a different
  List."""
  type = models.CharField(max_length=127, choices=(('list','list'), ('position','position')))
  item = models.ForeignKey(Item, models.SET_NULL, null=True, blank=True,
                           related_name='moves')
  old_display_order = models.IntegerField(null=True)
  new_display_order = models.IntegerField(null=True)
  old_parent = models.ForeignKey(ListItem, models.PROTECT, null=True, blank=True,
                                 related_name='moves_from')
  new_parent = models.ForeignKey(ListItem, models.PROTECT, null=True, blank=True,
                                 related_name='moves_to')
  visit = models.ForeignKey(Visit, models.PROTECT, related_name='editpages_move')
