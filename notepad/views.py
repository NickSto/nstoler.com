from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template.defaultfilters import escape, urlize
from django.conf import settings
from .models import Note
from traffic.lib import add_visit
from myadmin.lib import get_admin_cookie
import random as rand
import string

def notes(request, page):
  format = request.GET.get('format')
  show_deleted = request.GET.get('include') == 'deleted'
  # Only allow showing deleted notes to the admin over HTTPS.
  admin_cookie = get_admin_cookie(request)
  if not (admin_cookie and (request.is_secure() or not settings.REQUIRE_HTTPS)):
    show_deleted = False
  #TODO: Display deleted notes differently.
  if show_deleted:
    note_objects = Note.objects.filter(page=page)
  else:
    note_objects = Note.objects.filter(page=page, deleted=False)
  text = ''
  notes = []
  for note in note_objects:
    if format == 'plain':
      text += note.content
    else:
      lines = _format_note(note.content)
      notes.append((note.id, lines))
  if format == 'plain':
    response = HttpResponse(text, content_type='text/plain; charset=UTF-8')
    return add_visit(request, response)
  else:
    context = {'page':page, 'notes':notes}
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

def add(request):
  params = request.POST
  #TODO: Email warning about detected spambots.
  #TODO: Check if the notes were added to the main "notepad" page.
  response = redirect('notepad:notes', params['page'])
  traffic_data = {'visit':1}
  response = add_visit(request, response, side_effects=traffic_data)
  if params['site'] == '':
    note = Note(
      page=params['page'],
      content=params['content'],
      visit=traffic_data['visit']
    )
    note.save()
  return response

def delete(request):
  params = request.POST
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
          continue
        note.deleted = True
        note.save()
  #TODO: Email warning about detected spambots.
  #TODO: Check if the notes were deleted from the main "notepad" page.
  return add_visit(request, redirect('notepad:notes', params['page']))

def random(request):
  alphabet = string.ascii_lowercase
  page = ''.join([rand.choice(alphabet) for i in range(5)])
  return add_visit(request, redirect('notepad:notes', page))
