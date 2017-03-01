from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import Note
from traffic.lib import add_visit
import random as rand
import string

def notes(request, page):
  format = request.GET.get('format')
  #TODO: Allow showing deleted notes with ?include=deleted (but only with admin cookie).
  #TODO: Hyperlink urls, convert spaces to nbsp.
  #TODO: Make empty notes display properly.
  note_objects = Note.objects.filter(page=page, deleted=False)
  # Go through the notes, splitting multi-line content into a list of lines.
  text = ''
  notes = []
  for note in note_objects:
    lines = note.content.splitlines()
    if format == 'plain':
      text += '\n'.join(lines)+'\n\n'
    # Note list: note_id, content, is_bottom.
    notes.append([note.id, lines, False])
  # Set is_bottom on the last note to True.
  if notes:
    notes[-1][-1] = True
  if format == 'plain':
    response = HttpResponse(text, content_type='text/plain; charset=UTF-8')
    return add_visit(request, response)
  else:
    context = {'page':page, 'notes':notes}
    return add_visit(request, render(request, 'notepad/notes.tmpl', context))

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
