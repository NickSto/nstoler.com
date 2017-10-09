from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.template.defaultfilters import escape, urlize
from django.db.models import Max
from .models import Note, Page
from myadmin.lib import get_admin_cookie, require_admin_and_privacy
import random as rand
import string
import logging
log = logging.getLogger(__name__)


def view(request, page_name):
  params = request.GET
  format = params.get('format')
  admin = params.get('admin')
  try:
    note_id = int(params.get('note'))
  except (ValueError, TypeError):
    note_id = None
  show_deleted = params.get('include') == 'deleted'
  # Only allow showing deleted notes to the admin over HTTPS.
  admin_cookie = get_admin_cookie(request)
  if not (admin_cookie and (request.is_secure() or not settings.REQUIRE_HTTPS)):
    show_deleted = False
    admin = False
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
    context = {'page':page_name, 'notes':notes, 'admin':admin}
    return render(request, 'notepad/view.tmpl', context)


def add(request, page_name):
  params = request.POST
  #TODO: Check if the notes were added to the main "notepad" page.
  view_url = reverse('notepad:view', args=(page_name,))
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
    # Make the new display_order 1000 greater than the previous max, to give room to place notes
    # inbetween existing ones.
    display_order = max_display + 1000
    # Create the Note.
    note = Note(
      page=page,
      content=params.get('content', ''),
      visit=request.visit,
      display_order=display_order
    )
    note.save()
  else:
    #TODO: Email warning about detected spambots.
    site = truncate(params.get('site'))
    content = truncate(params.get('content'))
    log.warning('Spambot ({0}) blocked from adding to page "{1}". Ruhuman field: {2!r}, note: {3!r}'
                .format(request.visit.visitor, page_name, site, content))
  return HttpResponseRedirect(view_url+'#bottom')


def delete(request, page_name):
  params = request.POST
  view_url = reverse('notepad:view', args=(page_name,))
  if params.get('site') == '':
    for key in params:
      if key.startswith('note_'):
        try:
          note_id = int(key[5:])
        except ValueError:
          continue
        try:
          note = Note.objects.get(pk=note_id)
        except Note.DoesNotExist:
          log.info('Visitor "{}" tried to delete non-existent note #{}.'
                   .format(request.visit.visitor, note_id))
          continue
        note.deleted = True
        note.deleting_visit = request.visit
        note.save()
  else:
    #TODO: Email warning about detected spambots.
    site = truncate(params.get('site'))
    note_ids = [key[5:] for key in params.keys() if key.startswith('note_')]
    log.warning('Spambot ({0}) blocked from deleting notes {1} from page "{2}". Ruhuman field: {3!r}'
                .format(request.visit.visitor, ', '.join(note_ids), page_name, site))
  #TODO: Check if the notes were deleted from the main "notepad" page.
  return HttpResponseRedirect(view_url+'#bottom')


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
