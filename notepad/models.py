from django.db import models
from django.template.defaultfilters import escape, urlize
from traffic.models import Visit
from utils import ModelMixin


class Page(ModelMixin, models.Model):
  name = models.CharField(max_length=200)
  def __str__(self):
    return self.name


# For historical reasons, the terminology is now a little odd.
# Ideally, I'd have a `Note` class that represents a single note and all its versions.
# It would be associated with one or more `Version`s, which hold the actual text.
# But for now, the current `Note` class corresponds to the `Version` I just described.
# And there is no `Note` class like I described, just a `history` field in each `Note
# (to minimize database query complexity).
# But the ideal terminology is now the public one, exposed in the url query strings.

class Note(ModelMixin, models.Model):
  page = models.ForeignKey(Page, models.SET_NULL, null=True, blank=True)
  # An edit history of Notes.
  history = models.IntegerField(null=True)
  content = models.TextField()
  visit = models.ForeignKey(Visit, models.SET_NULL, null=True, blank=True)
  protected = models.BooleanField(default=False)  # Only admin can modify.
  archived = models.BooleanField(default=False)
  archiving_visit = models.ForeignKey(
    Visit, models.SET_NULL, null=True, blank=True, related_name='archived_note'
  )
  deleted = models.BooleanField(default=False)
  deleting_visit = models.ForeignKey(
    Visit, models.SET_NULL, null=True, blank=True, related_name='deleted_note'
  )
  display_order = models.IntegerField()
  last_version = models.OneToOneField(
    'self', models.SET_NULL, null=True, blank=True, related_name='next_version'
  )
  @property
  def edited(self):
    try:
      if self.next_version:
        return True
    except Note.DoesNotExist:
      return False
    return False
  @property
  def latest(self):
    latest = self
    while latest.edited:
      latest = latest.next_version
    return latest
  def content_html(self):
    urlized = urlize(escape(self.content))
    # Kludge to add some custom attributes to the <a> links.:
    return urlized.replace('rel="nofollow">', 'rel="noreferrer nofollow" target="_blank">')
  def __str__(self):
    deleted = ''
    if self.deleted:
      deleted = ' (deleted)'
    return '{}{}: {}'.format(self.page, deleted, repr(self.content[:50]))


class Move(ModelMixin, models.Model):
  """A record of an action that moves a note.
  A movement either moves the note to a different page or to a different display position on the
  same page."""
  type = models.CharField(max_length=127, choices=(('page','page'), ('position','position')))
  note = models.ForeignKey(Note, models.PROTECT)
  old_page = models.ForeignKey(Page, models.PROTECT, null=True, blank=True, related_name='moves_from')
  new_page = models.ForeignKey(Page, models.PROTECT, null=True, blank=True, related_name='moves_to')
  old_display_order = models.IntegerField(null=True)
  new_display_order = models.IntegerField(null=True)
  visit = models.ForeignKey(Visit, models.PROTECT)
