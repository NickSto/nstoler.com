from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.template.defaultfilters import escape, urlize
from django.conf import settings
from .models import Note, Page
from traffic.lib import add_visit, add_and_get_visit
from myadmin.lib import get_admin_cookie, require_admin_and_privacy
import random as rand
import string
import logging
log = logging.getLogger(__name__)


@add_visit
def view(request, page_name):
  params = request.GET
  format = params.get('format')
  admin = params.get('admin')
  show_deleted = params.get('include') == 'deleted'
  # Only allow showing deleted notes to the admin over HTTPS.
  admin_cookie = get_admin_cookie(request)
  if not (admin_cookie and (request.is_secure() or not settings.REQUIRE_HTTPS)):
    show_deleted = False
    admin = False
  #TODO: Display deleted notes differently.
  if show_deleted:
    note_objects = Note.objects.filter(page__name=page_name).order_by('id')
  else:
    note_objects = Note.objects.filter(page__name=page_name, deleted=False).order_by('id')
  notes = []
  for note in note_objects:
    if format == 'plain':
      notes.append(note.content)
    else:
      content_formatted = urlize(escape(note.content))
      notes.append((note, content_formatted))
  if format == 'plain':
    return HttpResponse('\n\n'.join(notes), content_type='text/plain; charset=UTF-8')
  else:
    context = {'page':page_name, 'notes':notes, 'admin':admin}
    return render(request, 'notepad/view.tmpl', context)


@add_and_get_visit
def add(request, visit, page_name):
  params = request.POST
  #TODO: Email warning about detected spambots.
  #TODO: Check if the notes were added to the main "notepad" page.
  view_url = reverse('notepad:view', args=(page_name,))
  if params['site'] == '':
    try:
      page = Page.objects.get(name=page_name)
    except Page.DoesNotExist:
      page = Page(
        name=page_name
      )
      page.save()
    note = Note(
      page=page,
      content=params['content'],
      visit=visit
    )
    note.save()
  return HttpResponseRedirect(view_url+'#bottom')


@add_and_get_visit
def delete(request, visit, page_name):
  params = request.POST
  view_url = reverse('notepad:view', args=(page_name,))
  if params['site'] == '':
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
                   .format(visit.visitor, note_id))
          continue
        note.deleted = True
        note.deleting_visit = visit
        note.save()
  #TODO: Email warning about detected spambots.
  #TODO: Check if the notes were deleted from the main "notepad" page.
  return HttpResponseRedirect(view_url+'#bottom')


@add_visit
def random(request):
  alphabet = string.ascii_lowercase
  page_name = ''.join([rand.choice(alphabet) for i in range(5)])
  return redirect('notepad:view', page_name)


@add_visit
@require_admin_and_privacy
def monitor(request):
  format = request.GET.get('format')
  pages = Page.objects.order_by('name')
  if format == 'plain':
    text = '\n'.join([page.name for page in pages])
    return HttpResponse(text, content_type='text/plain; charset=UTF-8')
  else:
    context = {'pages':pages}
    return render(request, 'notepad/monitor.tmpl', context)
