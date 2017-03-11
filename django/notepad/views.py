from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template.defaultfilters import escape, urlize
from django.conf import settings
from .models import Note, Page
from traffic.lib import add_visit
from myadmin.lib import get_admin_cookie
import random as rand
import string

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
  text = ''
  notes = []
  for note in note_objects:
    if format == 'plain':
      text += note.content
    else:
      lines = _format_note(note.content)
      notes.append((note, lines))
  if format == 'plain':
    response = HttpResponse(text, content_type='text/plain; charset=UTF-8')
    return add_visit(request, response)
  else:
    context = {'page':page_name, 'notes':notes, 'admin':admin}
    return add_visit(request, render(request, 'notepad/notes.tmpl', context))

def _format_note(content):
  if content:
    lines = content.splitlines()
  else:
    lines = ['']
  lines_formatted = []
  for line in lines:
    line = escape(line)
    line = urlize(line)
    if line == '':
      line = ' '
    lines_formatted.append(line)
  return lines_formatted

def add(request, page_name):
  params = request.POST
  #TODO: Email warning about detected spambots.
  #TODO: Check if the notes were added to the main "notepad" page.
  response = redirect('notepad:view', page_name)
  traffic_data = {'visit':1}
  response = add_visit(request, response, side_effects=traffic_data)
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
      visit=traffic_data['visit']
    )
    note.save()
  return response

def delete(request, page_name):
  params = request.POST
  response = redirect('notepad:view', page_name)
  traffic_data = {'visit':1}
  response = add_visit(request, response, side_effects=traffic_data)
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
          logging.info('Visitor "{}"" tried to delete non-existent note #{}.'
                       .format(traffic_data['visit'].visitor, note_id))
          continue
        note.deleted = True
        note.deleting_visit = traffic_data['visit']
        note.save()
  #TODO: Email warning about detected spambots.
  #TODO: Check if the notes were deleted from the main "notepad" page.
  return response

def random(request):
  alphabet = string.ascii_lowercase
  page_name = ''.join([rand.choice(alphabet) for i in range(5)])
  return add_visit(request, redirect('notepad:view', page_name))

def monitor(request):
  format = request.GET.get('format')
  # Only show global list of pages to the admin over HTTPS.
  admin_cookie = get_admin_cookie(request)
  if not (admin_cookie and (request.is_secure() or not settings.REQUIRE_HTTPS)):
    text = 'You are not authorized for this content.'
    return add_visit(request, HttpResponse(text, content_type='text/plain; charset=UTF-8'))
  pages = Page.objects.order_by('name')
  if format == 'plain':
    text = '\n'.join([page.name for page in pages])
    return add_visit(request, HttpResponse(text, content_type='text/plain; charset=UTF-8'))
  else:
    context = {'pages':pages}
    return add_visit(request, render(request, 'notepad/monitor.tmpl', context))
