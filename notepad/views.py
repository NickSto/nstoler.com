from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.template.defaultfilters import escape, urlize
from django.db.models import Max
import django.db
from .models import Note, Page, Move
from myadmin.lib import get_admin_cookie, require_admin_and_privacy
import random as rand
import string
import logging
log = logging.getLogger(__name__)

DISPLAY_ORDER_MARGIN = 1000


def view(request, page_name):
  params = request.GET
  format = params.get('format')
  admin_view = params.get('admin')
  try:
    note_id = int(params.get('note'))
  except (ValueError, TypeError):
    note_id = None
  show_deleted = params.get('include') == 'deleted'
  # Only allow showing deleted notes to the admin over HTTPS.
  if not is_admin_and_secure(request):
    show_deleted = False
    admin_view = False
  #TODO: Display deleted notes differently.
  if show_deleted:
    note_objects = Note.objects.filter(page__name=page_name).order_by('display_order', 'id')
  else:
    note_objects = Note.objects.filter(page__name=page_name, deleted=False).order_by('display_order', 'id')
  notes = []
  for note in note_objects:
    if note_id is not None and note.id != note_id:
      continue
    if format == 'plain':
      notes.append(note.content)
    else:
      content_formatted = urlize(escape(note.content))
      notes.append((note, content_formatted))
  if format == 'plain':
    return HttpResponse('\n\n'.join(notes), content_type=settings.PLAINTEXT)
  else:
    context = {'page':page_name, 'notes':notes, 'admin':admin_view}
    return render(request, 'notepad/view.tmpl', context)


def add(request, page_name):
  params = request.POST
  #TODO: Check if the notes were added to the main "notepad" page.
  if params.get('site') == '':
    # Get or create the Page.
    try:
      page = Page.objects.get(name=page_name)
    except Page.DoesNotExist:
      page = Page(
        name=page_name
      )
      page.save()
    # Find the highest display_order currently on the page.
    stats = Note.objects.filter(page__name=page_name).aggregate(Max('display_order'))
    max_display = stats.get('display_order__max')
    if max_display is None:
      max_display = 0
    # Make the new display_order a lot greater than the previous max, to give room to place notes
    # inbetween existing ones.
    display_order = max_display + DISPLAY_ORDER_MARGIN
    # Create the Note.
    note = Note(
      page=page,
      content=params.get('content', ''),
      visit=request.visit,
      display_order=display_order
    )
    note.save()
  else:
    warn_and_redirect_spambot(request, page_name, 'adding a note')
  view_url = reverse('notepad:view', args=(page_name,))
  return HttpResponseRedirect(view_url+'#bottom')


def confirm(request, page_name):
  params = request.POST
  notes = get_notes_from_params(params)
  if params.get('site') == '':
    notes_list = []
    for note in notes:
      content_formatted = urlize(escape(note.content))
      notes_list.append((note, content_formatted))
    context = {'page':page_name, 'notes':notes_list}
    return render(request, 'notepad/confirm.tmpl', context)
  else:
    warn_and_redirect_spambot(request, page_name, 'deleting notes', notes)
  view_url = reverse('notepad:view', args=(page_name,))
  return HttpResponseRedirect(view_url+'#bottom')


def delete(request, page_name):
  params = request.POST
  notes = get_notes_from_params(params)
  admin = None
  if params.get('site') == '':
    for note in notes:
      if note.protected:
        if admin is None:
          admin = is_admin_and_secure(request)
        if not admin:
          log.warning('Non-admin attempted to delete protected note {!r}.'.format(note.id))
          continue
      note.deleted = True
      note.deleting_visit = request.visit
      note.save()
  else:
    warn_and_redirect_spambot(request, page_name, 'confirming note deletions', notes)
  #TODO: Check if the notes were deleted from the main "notepad" page.
  view_url = reverse('notepad:view', args=(page_name,))
  return HttpResponseRedirect(view_url+'#bottom')


def editform(request, page_name):
  view_url = reverse('notepad:view', args=(page_name,))
  params = request.POST
  notes = get_notes_from_params(params)
  if params.get('site') != '':
    return warn_and_redirect_spambot(request, page_name, 'editing notes', notes, view_url)
  error = None
  warning = None
  if len(notes) == 0:
    log.warning('No valid note selected for editing.')
    error = 'No valid note selected.'
    note = None
  elif len(notes) > 1:
    log.info('Multiple notes selected.')
    warning = 'Multiple notes selected. Editing only the first one.'
    note = notes[0]
  else:
    note = notes[0]
  if note and note.protected and not is_admin_and_secure(request):
    log.warning('Non-admin attempted to edit protected note {}.'.format(note.id))
    error = 'This note is protected.'
  if error:
    context = {'page':page_name, 'error':error}
    return render(request, 'notepad/error.tmpl', context)
  elif note:
    lines = len(note.content.splitlines())
    context = {'page':page_name, 'note':note, 'rows':round(lines*1.1)+2, 'warning':warning}
    return render(request, 'notepad/editform.tmpl', context)
  else:
    log.error('Ended up with neither a note ({!r}) nor an error ({!r}).'.format(note, error))
    return HttpResponseRedirect(view_url)


def edit(request, page_name):
  view_url = reverse('notepad:view', args=(page_name,))
  fragment = '#bottom'
  params = request.POST
  if params.get('site') != '':
    notes = [params.get('note')]
    return warn_and_redirect_spambot(request, page_name, 'editing note', notes, view_url+fragment)
  try:
    note_id = int(params.get('note'))
  except (TypeError, ValueError):
    log.warning('Invalid note id for editing: {!r}'.format(params.get('note')))
    return HttpResponseRedirect(view_url+fragment)
  try:
    note = Note.objects.get(pk=note_id)
  except Note.DoesNotExist:
    log.warning('Visitor "{}" tried to submit an edit to non-existent note #{}.'
                .format(request.visit.visitor, note_id))
    return HttpResponseRedirect(view_url+fragment)
  fragment = '#note_{}'.format(note_id)
  if note.protected and not is_admin_and_secure(request):
    return HttpResponseRedirect(view_url+fragment)
  if 'content' not in params:
    log.warning('No "content" key in query parameters.')
    return HttpResponseRedirect(view_url+fragment)
  try:
    page = Page.objects.get(name=page_name)
  except Page.DoesNotExist:
    log.warning('Page {!r} does not exist.'.format(page_name))
    return HttpResponseRedirect(view_url+fragment)
  edited_note = Note(
    page=page,
    content=params.get('content', ''),
    visit=request.visit,
    display_order=note.display_order+1,
    protected=note.protected,
    last_version=note
  )
  note.deleted = True
  note.deleting_visit = request.visit
  # Save both or, if something goes wrong, neither.
  try:
    edited_note.save()
    note.save()
  except django.db.Error as dbe:
    log.error('Error on saving edited note: {}'.format(dbe))
  fragment = '#note_{}'.format(edited_note.id)
  return HttpResponseRedirect(view_url+fragment)


def moveform(request, old_page_name):
  view_url = reverse('notepad:view', args=(old_page_name,))
  params = request.POST
  notes = get_notes_from_params(params)
  if params.get('site') != '':
    return warn_and_redirect_spambot(request, old_page_name, 'moving notes', notes, view_url)
  notes_list = []
  for note in notes:
    content_formatted = urlize(escape(note.content))
    notes_list.append((note, content_formatted))
  context = {'page':old_page_name, 'notes':notes_list}
  return render(request, 'notepad/moveform.tmpl', context)


def move(request, old_page_name):
  view_url = reverse('notepad:view', args=(old_page_name,))
  params = request.POST
  notes = get_notes_from_params(params)
  if params.get('site') != '':
    return warn_and_redirect_spambot(request, old_page_name, 'confirming move of notes', notes, view_url)
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
      move.save()
      note.save()
    except django.db.Error as dbe:
      log.error('Error on saving Move or Note: {}'.format(dbe))
  return HttpResponseRedirect(view_url)


def warn_and_redirect_spambot(request, page_name, action, notes=None, view_url=None):
  #TODO: Email warning about detected spambots.
  params = request.POST
  site = truncate(params.get('site'))
  if notes:
    note_ids = [str(getattr(note, 'id', note)) for note in notes]
    notes_str = ' '+', '.join(note_ids)
  else:
    notes_str = ''
  log.warning('Spambot ({0}) blocked from {1}{2} from page "{3}". Ruhuman field: {4!r}'
              .format(request.visit.visitor, action, notes_str, page_name, site))
  if view_url is not None:
    return HttpResponseRedirect(view_url)


def get_notes_from_params(params):
  note_id_strs = [key[5:] for key in params.keys() if key.startswith('note_')]
  notes = []
  for note_id_str in note_id_strs:
    try:
      note_id = int(note_id_str)
    except ValueError:
      log.warning('Non-integer note number in {!r}'.format(note_id_str))
      continue
    try:
      note = Note.objects.get(pk=note_id)
    except Note.DoesNotExist:
      log.warning('Non-existent note {!r}.'.format(note_id))
      continue
    notes.append(note)
  notes.sort(key=lambda note: (note.display_order, note.id))
  return notes


def is_admin_and_secure(request):
  admin_cookie = get_admin_cookie(request)
  return admin_cookie and (request.is_secure() or not settings.REQUIRE_HTTPS)


def truncate(s, max_len=100):
  if s is not None and len(s) > max_len:
    return s[:max_len]+'...'
  else:
    return s


def random(request):
  alphabet = string.ascii_lowercase
  page_name = ''.join([rand.choice(alphabet) for i in range(5)])
  return redirect('notepad:view', page_name)


@require_admin_and_privacy
def monitor(request):
  format = request.GET.get('format')
  pages = Page.objects.order_by('name')
  if format == 'plain':
    text = '\n'.join([page.name for page in pages])
    return HttpResponse(text, content_type=settings.PLAINTEXT)
  else:
    context = {'pages':pages}
    return render(request, 'notepad/monitor.tmpl', context)
