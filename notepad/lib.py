import logging
from django.db import transaction, DatabaseError
from .models import Note
log = logging.getLogger(__name__)

DISPLAY_ORDER_MARGIN = 1000


def get_notes_from_ids(note_ids, *args, **kwargs):
  filters = make_filters(*args, **kwargs)
  notes_dict = Note.objects.filter(**filters).in_bulk(note_ids)
  notes = list(notes_dict.values())
  notes.sort(key=lambda note: (note.display_order, note.id))
  return notes


def get_notes(*args, **kwargs):
  filters = make_filters(*args, **kwargs)
  return Note.objects.filter(**filters).order_by('display_order', 'id')


def make_filters(page_name=None, archived=True, deleted=True):
  filters = {}
  if page_name is not None:
    filters['page__name'] = page_name
  if not archived:
    filters['archived'] = False
  if not deleted:
    filters['deleted'] = False
  return filters


def create_note(page, content, visit, protected=False):
  note = Note(
    page=page,
    content=content,
    visit=visit,
    protected=protected,
    history=-1,
    display_order=1,
  )
  note.save()
  # Set the display order to a multiple of its id. This should be greater than any other
  # display_order, putting it last on the page. It should also keep the display_orders of notes
  # across all pages increasing chronologically by default, giving a nicer order when moving a
  # note into an existing page with other notes.
  note.display_order = note.id * DISPLAY_ORDER_MARGIN
  note.history = note.id
  note.save()
  return note


def edit_note(old_version, new_content, visit):
  new_version = Note(
    page=old_version.page,
    content=new_content,
    visit=visit,
    display_order=old_version.display_order,
    protected=old_version.protected,
    history=old_version.history,
    last_version=old_version,
  )
  old_version.deleted = True
  old_version.deleting_visit = visit
  # Save both or, if something goes wrong, neither.
  try:
    with transaction.atomic():
      old_version.save()
      new_version.save()
  except DatabaseError as dbe:
    log.error(f'Error on saving edited note: {dbe}')
    raise
  return new_version


def get_latest_version(history_id, *args, **kwargs):
  filters = {
    'history': history_id,
    'next_version__isnull': True,
  }
  user_filters = make_filters(*args, **kwargs)
  filters.update(user_filters)
  try:
    note = Note.objects.get(**filters)
  except Note.DoesNotExist:
    criteria_str = ', '.join([f'{key}={value!r}' for key, value in user_filters.items()])
    log.error(f'The most recent note of history {history_id} does not fit criteria {criteria_str}.')
  except Note.MultipleObjectsReturned:
    criteria_str = ', '.join([f'{key}={value!r}' for key, value in user_filters.items()])
    log.error(
      f'Multiple notes appear to be the latest in history {history_id} (criteria {criteria_str}.'
    )
  else:
    return note
