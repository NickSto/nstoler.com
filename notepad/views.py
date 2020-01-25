from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.template.defaultfilters import escape, urlize
from django.db import transaction
from django.db.models import Max
import django.db
from myadmin.lib import is_admin_and_secure, require_admin_and_privacy
from traffic.categorize import is_bot_request, HONEYPOT_NAME, get_checked_boxes
from utils.queryparams import QueryParams, boolish
from utils import email_admin
from .models import Note, Page, Move
import collections
import random as rand
import string
import logging
log = logging.getLogger(__name__)

PROTECTED_PAGES = ('notepad',)
DISPLAY_ORDER_MARGIN = 1000


@require_admin_and_privacy
def monitor(request):
  params = QueryParams()
  params.add('format', default='html', choices=('html', 'plain'))
  params.add('deleted', type=boolish, default=False, choices=(True, False))
  params.parse(request.GET)
  # If one of the parameters was invalid, redirect to a fixed url.
  # - QueryParams object will automatically set the parameter to a valid value.
  if params.invalid_value:
    return HttpResponseRedirect(reverse('notepad:monitor')+str(params))
  if params['deleted']:
    pages = Page.objects.order_by('name')
    pages = sorted(pages, key=lambda page: page.name.lower())
  else:
    notes = Note.objects.filter(deleted=False).distinct('page')
    pages = sorted([note.page for note in notes], key=lambda page: page.name.lower())
  if params['format'] == 'plain':
    text = '\n'.join([page.name for page in pages])
    return HttpResponse(text, content_type=settings.PLAINTEXT)
  else:
    if params['deleted']:
      deleted_query_str = str(params.but_with(deleted=False))
    else:
      deleted_query_str = str(params.but_with(deleted=True))
    context = {
      'pages':pages, 'deleted':params['deleted'], 'deleted_query_str':deleted_query_str,
    }
    return render(request, 'notepad/monitor.tmpl', context)
#TODO: Return TemplateResponses instead of doing the rendering directly.


def view(request, page_name):
  params = QueryParams()
  params.add('note', type=int, default=None)
  params.add('version', type=int, default=None)
  params.add('format', default='html', choices=('html', 'plain'))
  params.add('admin', type=boolish, default=False, choices=(True, False))
  params.add('archived', type=boolish, default=False, choices=(True, False))
  params.add('deleted', type=boolish, default=False, choices=(True, False))
  params.add('select', default='none', choices=('all', 'none'))
  params.parse(request.GET)
  # If one of the parameters was invalid, redirect to a fixed url.
  # - QueryParams object will automatically set the parameter to a valid value.
  if params.invalid_value:
    return HttpResponseRedirect(reverse('notepad:view', args=(page_name,))+str(params))
  # Only allow showing deleted notes to the admin over HTTPS.
  is_admin = is_admin_and_secure(request)
  if not is_admin and (params['admin'] or params['deleted']):
    query_str = str(params.but_with(admin=False, deleted=False))
    return HttpResponseRedirect(reverse('notepad:view', args=(page_name,))+query_str)
  # Fetch the note(s).
  if params['version']:
    notes = get_notes_from_ids([params['version']], page_name, params['archived'], params['deleted'])
  elif params['note']:
    note = get_latest_version(params['note'], page_name, params['archived'], params['deleted'])
    notes = [note]
  else:
    notes = get_notes(page_name, params['archived'], params['deleted'])
  # Bundle up the data and display the notes.
  if params['format'] == 'plain':
    contents = [note.content for note in notes]
    return HttpResponse('\n\n'.join(contents), content_type=settings.PLAINTEXT)
  else:
    links = collections.OrderedDict()
    randomness = rand.randint(1, 1000000)
    links['☑ Select all'] = str(params.but_with(select='all', reload=randomness))
    links['□ Select none'] = str(params.but_with(select='none', reload=randomness))
    if is_admin:
      if params['admin']:
        links['Admin off'] = str(params.but_with(admin=False))
      else:
        links['Admin on'] = str(params.but_with(admin=True))
    if params['archived']:
      links['Hide archived'] = str(params.but_with(archived=False))
    else:
      links['Show archived'] = str(params.but_with(archived=True))
    if is_admin:
      if params['deleted']:
        links['Hide deleted'] = str(params.but_with(deleted=False))
      else:
        links['Show deleted'] = str(params.but_with(deleted=True))
    context = {
      'page':page_name, 'notes':notes, 'links':links, 'admin_view':params['admin'],
      'select':params['select'],
    }
    return render(request, 'notepad/view.tmpl', context)


def add(request, page_name):
  params = request.POST
  spam = is_bot_request(request)
  if spam:
    if not spam.is_boring:
      # Don't even email about run-of-the-mill spammers.
      activity_notify(request, page_name, 'adding a note')
  else:
    # Get or create the Page.
    try:
      page = Page.objects.get(name=page_name)
    except Page.DoesNotExist:
      page = Page(
        name=page_name
      )
      page.save()
    # Create the Note.
    note = Note(
      page=page,
      content=params.get('content', ''),
      visit=request.visit,
      display_order=1
    )
    note.save()
    # Set the display order to a multiple of its id. This should be greater than any other
    # display_order, putting it last on the page. It should also keep the display_orders of notes
    # across all pages increasing chronologically by default, giving a nicer order when moving a
    # note into an existing page with other notes.
    note.display_order = note.id * DISPLAY_ORDER_MARGIN
    note.history = note.id
    note.save()
    if page_name in PROTECTED_PAGES:
      # Notify that someone added a note to a protected page.
      activity_notify(request, page_name, 'adding a note', blocked=False)
  view_url = reverse('notepad:view', args=(page_name,))
  return HttpResponseRedirect(view_url+'#bottom')


def hideform(request, page_name):
  params = request.POST
  action = params.get('action')
  notes = get_notes_from_params(params)
  if action in ('archive', 'delete'):
    context = {'page':page_name, 'notes':notes, 'action':action}
    return render(request, 'notepad/hideform.tmpl', context)
  else:
    log.warning(f'Invalid hide action {action!r}.')
    view_url = reverse('notepad:view', args=(page_name,))
    return HttpResponseRedirect(view_url+'#bottom')


def hide(request, page_name):
  params = request.POST
  action = params.get('action')
  notes = get_notes_from_params(params)
  admin = None
  if is_bot_request(request):
    activity_notify(request, page_name, f'{action}-ing', notes)
  elif action in ('archive', 'delete'):
    for note in notes:
      if note.page.name != page_name:
        log.warning('User attempted to {} note {} from page {!r}, but gave page name {!r}'
                    .format(action, note.id, note.page.name, page_name))
        continue
      if note.protected:
        if admin is None:
          admin = is_admin_and_secure(request)
        if not admin:
          log.warning('Non-admin attempted to delete protected note {!r}.'.format(note.id))
          continue
      if action == 'archive':
        note.archived = True
        note.archiving_visit = request.visit
      elif action == 'delete':
        note.deleted = True
        note.deleting_visit = request.visit
      note.save()
    if page_name in PROTECTED_PAGES:
      # Notify that someone archived/deleted notes from a protected page.
      activity_notify(request, page_name, f'{action}-ing note(s)', notes, blocked=False)
  view_url = reverse('notepad:view', args=(page_name,))
  return HttpResponseRedirect(view_url+'#bottom')


def editform(request, page_name):
  view_url = reverse('notepad:view', args=(page_name,))
  params = request.POST
  notes = get_notes_from_params(params)
  error = None
  warning = None
  if len(notes) == 0:
    note_ids = get_note_ids_from_params(params)
    notes_str = ', '.join([str(note_id) for note_id in note_ids])
    log.warning(f'No valid note selected for editing. User selected {notes_str}')
    error = 'No valid note selected.'
    note = None
  elif len(notes) > 1:
    log.info('Multiple notes selected.')
    warning = 'Multiple notes selected. Editing only the first one.'
    note = notes[0]
  else:
    note = notes[0]
  # Prevent appearance of being able to edit protected, archived, or deleted notes.
  if not note:
    pass
  elif note.protected and not is_admin_and_secure(request):
    log.warning('Non-admin attempted to edit protected note {}.'.format(note.id))
    error = 'This note is protected.'
  elif note.edited:
    log.warning(f'User attempted to edit already edited note {note.id}.')
    error = 'This note has already been edited.'
  elif note.archived:
    log.warning(f'User attempted to edit archived note {note.id}.')
    error = 'This note has been archived.'
  elif note.deleted:
    log.warning(f'User attempted to edit deleted note {note.id}.')
    error = 'This note has been deleted.'
  if error:
    context = {'page':page_name, 'error':error}
    #TODO: Return a non-200 HTTP status.
    return render(request, 'notepad/error.tmpl', context)
  elif note:
    notes = get_notes(page_name, archived=False, deleted=False)
    lines = len(note.content.splitlines())
    context = {
      'page':page_name, 'note':note, 'notes':notes, 'rows':round(lines*1.1)+2, 'warning':warning,
    }
    return render(request, 'notepad/editform.tmpl', context)
  else:
    log.error(f'Ended up with neither a note ({note!r}) nor an error ({error!r}).')
    return HttpResponseRedirect(view_url)


def edit(request, page_name):
  view_url = reverse('notepad:view', args=(page_name,))
  redirect_url = view_url+'#bottom'
  params = request.POST
  if is_bot_request(request):
    notes = [params.get('note')]
    return activity_notify(request, page_name, 'editing note', notes, redirect_url)
  # Get the Note requested.
  try:
    note_id = int(params.get('note'))
  except (TypeError, ValueError):
    log.warning('Invalid note id for editing: {!r}'.format(params.get('note')))
    return HttpResponseRedirect(redirect_url)
  try:
    note = Note.objects.get(pk=note_id)
  except Note.DoesNotExist:
    log.warning(
      f'Visitor "{request.visit.visitor}" tried to submit an edit to non-existent note #{note_id}.'
    )
    return HttpResponseRedirect(redirect_url)
  redirect_url = f'{view_url}#note_{note_id}'
  # Verify that everything looks valid.
  if note.page.name != page_name:
    log.warning(
        f'User tried to edit note {note.id!r} from page {note.page.name!r}, but gave page name '
        f'{page_name!r}.'
    )
    return HttpResponseRedirect(redirect_url)
  if note.protected and not is_admin_and_secure(request):
    # Prevent editing protected notes.
    log.warning(f'User tried to edit protected note {note.id} from page {note.page.name!r}.')
    return HttpResponseRedirect(redirect_url)
  if note.deleted:
    log.warning(f'User tried to edit deleted note {note.id} from page {note.page.name!r}.')
    return HttpResponseRedirect(redirect_url)
  if note.archived:
    log.warning(f'User tried to edit archived note {note.id} from page {note.page.name!r}.')
    return HttpResponseRedirect(redirect_url)
  # Double-check this note hasn't already been edited.
  if note.edited:
    log.warning(f'User tried to edit already-edited note {note.id} from page {note.page.name!r}.')
    return HttpResponseRedirect(redirect_url)
  if 'content' not in params:
    log.warning('No "content" key in query parameters.')
    return HttpResponseRedirect(redirect_url)
  try:
    page = Page.objects.get(name=page_name)
  except Page.DoesNotExist:
    log.warning('Page {!r} does not exist.'.format(page_name))
    return HttpResponseRedirect(redirect_url)
  edited_note = Note(
    page=page,
    content=params.get('content', ''),
    visit=request.visit,
    display_order=note.display_order,
    protected=note.protected,
    history=note.history,
    last_version=note,
  )
  note.deleted = True
  note.deleting_visit = request.visit
  # Save both or, if something goes wrong, neither.
  try:
    with transaction.atomic():
      edited_note.save()
      note.save()
  except django.db.Error as dbe:
    log.error('Error on saving edited note: {}'.format(dbe))
  if page_name in PROTECTED_PAGES:
    # Notify that someone edited a note from a protected page.
    activity_notify(request, page_name, f'editing a note', [note], blocked=False)
  redirect_url = f'{view_url}#note_{edited_note.id}'
  return HttpResponseRedirect(redirect_url)


def moveform(request, page_name):
  view_url = reverse('notepad:view', args=(page_name,))
  params = request.POST
  notes = get_notes_from_params(params, archived=False, deleted=False)
  if not is_admin_and_secure(request):
    # Prevent appearance of being able to move protected notes.
    notes = [note for note in notes if not note.protected]
  context = {'page':page_name, 'notes':notes}
  return render(request, 'notepad/moveform.tmpl', context)


def move(request, page_name):
  view_url = reverse('notepad:view', args=(page_name,))
  params = request.POST
  notes = get_notes_from_params(params, archived=False, deleted=False)
  if is_bot_request(request):
    return activity_notify(request, page_name, 'moving notes', notes, view_url)
  action = params.get('action')
  if page_name in PROTECTED_PAGES:
    # Notify that someone moved a note on a protected page.
    activity_notify(request, page_name, f'moving a note', notes, blocked=False)
  if action == 'movepage':
    return _move_page(request, page_name, notes)
  elif action in ('moveup', 'movedown'):
    return _move_order(request, page_name, notes, action[4:])
  else:
    log.error('Unrecognized move action {!r}.'.format(action))
    return HttpResponseRedirect(view_url)


def _move_page(request, old_page_name, notes):
  view_url = reverse('notepad:view', args=(old_page_name,))
  params = request.POST
  new_page_name = params.get('new_page')
  if new_page_name:
    view_url = reverse('notepad:view', args=(new_page_name,))
  else:
    log.warning('No new_page received for move.')
    return HttpResponseRedirect(view_url)
  try:
    old_page = Page.objects.get(name=old_page_name)
  except Page.DoesNotExist:
    log.warning('Page {!r} does not exist.'.format(old_page_name))
    return HttpResponseRedirect(view_url)
  try:
    new_page = Page.objects.get(name=new_page_name)
  except Page.DoesNotExist:
    new_page = Page(name=new_page_name)
    new_page.save()
  for note in notes:
    if note.page.name != old_page_name:
      log.warning('User tried to move note {!r} from page {!r}, but gave page name {!r}.'
                  .format(note.id, note.page.name, old_page_name))
      continue
    if note.protected and not is_admin_and_secure(request):
      # Prevent moving protected notes.
      continue
    move = Move(
      type='page',
      note=note,
      old_page=old_page,
      new_page=new_page,
      visit=request.visit,
    )
    note.page = new_page
    # Save both or, if something goes wrong, neither.
    try:
      with transaction.atomic():
        move.save()
        note.save()
    except django.db.Error as dbe:
      log.error('Error on saving Move or Note: {}'.format(dbe))
  return HttpResponseRedirect(view_url)


def _move_order(request, page_name, notes, direction):
  page_notes = get_notes(page_name, archived=False, deleted=False)
  # Save old display_orders.
  old_orders = {}
  for note in page_notes:
    old_orders[note.id] = note.display_order
  # Go through the notes in the opposite direction they're moving in.
  # E.g. if we're moving notes down, then start from the last note and move up.
  reverse_order = direction == 'down'
  sorted_notes = sorted(page_notes, reverse=reverse_order, key=lambda note: (note.display_order, note.id))
  # Set new display_orders.
  for i in range(len(sorted_notes)):
    note = sorted_notes[i]
    if i == 0:
      # We can't move this note earlier, since it's already at the end.
      continue
    last_note = sorted_notes[i-1]
    if note not in notes:
      # This isn't one of the notes being moved.
      continue
    if last_note in notes:
      # Don't swap a note with another note being moved. They should all move in a block.
      # If a bunch of notes in a block are already at the end, the first rule (i == 0) prevents the
      # note at the end from moving, and this prevents the others in the block from moving past it.
      continue
    if note.protected and not is_admin_and_secure(request):
      # Prevent moving protected notes.
      continue
    # Swap display orders.
    note.display_order, last_note.display_order = last_note.display_order, note.display_order
    # Swap positions in the list.
    sorted_notes[i] = last_note
    sorted_notes[i-1] = note
  # Create Moves and save changes to database.
  for note in page_notes:
    if note.page.name != page_name:
      log.warning('User tried to move note {!r} order on page {!r}, but gave page name {!r}.'
                  .format(note.id, note.page.name, page_name))
      continue
    if note.display_order == old_orders[note.id]:
      continue
    move = Move(
      type='order',
      note=note,
      old_display_order=old_orders[note.id],
      new_display_order=note.display_order,
      visit=request.visit,
    )
    log.info('Moving note {} display_order from {} to {}.'
             .format(note.id, move.old_display_order, move.new_display_order))
    # Save both or, if something goes wrong, neither.
    try:
      with transaction.atomic():
        move.save()
        note.save()
    except django.db.Error as dbe:
      log.error('Error on saving Move or Note: {}'.format(dbe))
  view_url = reverse('notepad:view', args=(page_name,))
  return HttpResponseRedirect(view_url+'#bottom')


def activity_notify(request, page_name, action, notes=None, view_url=None, blocked=True):
  params = request.POST
  honey_value = truncate(params.get(HONEYPOT_NAME))
  if notes:
    note_ids = [str(getattr(note, 'id', note)) for note in notes]
    notes_str = ' '+', '.join(note_ids)
  else:
    notes_str = ''
  content = params.get('content')
  if content is None:
    content_line = ''
  else:
    content_line = 'Content: {}'.format(content)
  cookies = []
  for cookie in request.visit.cookies_got.all():
    cookies.append('{}:\t{}'.format(cookie.name, cookie.value))
  if blocked:
    result_str = 'blocked from'
    subject = 'Spambot blocked'
  else:
    result_str = 'seen'
    subject = 'Notepad alert'
  cookies_str = '\n  '+'\n  '.join(cookies)
  meta_str = ''
  for key in ('jsEnabled',):
    value = params.get(key)
    meta_str += f'\n  {key}:\t{value!r}'
  checked_boxes = get_checked_boxes(params)
  boxes_str = ', '.join([str(box) for box in checked_boxes])
  log.warning(
    f'Visitor ({request.visit.visitor}) {result_str} {action}{notes_str} on page {page_name!r}. '
    f'Ruhuman field: {honey_value!r}, Checked boxes: {boxes_str}'
  )
  email_body = f"""
Visitor from {request.visit.visitor.ip} {result_str} {action}{notes_str} on page {page_name!r}.
Ruhuman field: {honey_value!r}
Checked boxes: {boxes_str}
User agent: {request.visit.visitor.user_agent}
Metadata seen:{meta_str}
Cookies sent:{cookies_str}
{content_line}"""
  email_admin(subject, email_body)
  if view_url is not None:
    return HttpResponseRedirect(view_url)


########## NOTE RETRIEVAL ##########

def get_notes(*args, **kwargs):
  filters = make_filters(*args, **kwargs)
  return Note.objects.filter(**filters).order_by('display_order', 'id')


def get_notes_from_params(params, *args, **kwargs):
  note_ids = get_note_ids_from_params(params)
  return get_notes_from_ids(note_ids, *args, **kwargs)


def get_note_ids_from_params(params):
  note_ids = []
  for key, value in params.items():
    if key.startswith('note_') and value == 'on':
      try:
        note_id = int(key[5:])
      except ValueError:
        log.warning(f'Non-integer note number in {key!r}')
      else:
        note_ids.append(note_id)
  return note_ids


def get_notes_from_ids(note_ids, *args, **kwargs):
  filters = make_filters(*args, **kwargs)
  notes_dict = Note.objects.filter(**filters).in_bulk(note_ids)
  notes = list(notes_dict.values())
  notes.sort(key=lambda note: (note.display_order, note.id))
  return notes


def get_latest_version(history_id, *args, **kwargs):
  user_filters = make_filters(*args, **kwargs)
  version_filters = {
    'history': history_id,
    'next_version__isnull': True,
  }
  filters = user_filters.copy()
  filters.update(version_filters)
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


def make_filters(page_name=None, archived=True, deleted=True):
  filters = {}
  if page_name is not None:
    filters['page__name'] = page_name
  if not archived:
    filters['archived'] = False
  if not deleted:
    filters['deleted'] = False
  return filters


def truncate(s, max_len=100):
  if s is not None and len(s) > max_len:
    return s[:max_len]+'...'
  else:
    return s


def random(request):
  alphabet = string.ascii_lowercase
  page_name = ''.join([rand.choice(alphabet) for i in range(5)])
  return redirect('notepad:view', page_name)
