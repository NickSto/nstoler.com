from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render, redirect
from .models import Note
from traffic.lib import add_visit
import random as rand
import string

def notes(request, page):
  notes = Note.objects.filter(page=page)
  #TODO: Handle multi-line notes. Will have to iterate through notes and create our own list.
  bottom = None
  if notes:
    bottom = notes[len(notes)-1].id
  #TODO: Plaintext format if "format" parameter is true.
  #TODO: Take care of navbar (and the rest of the boilerplate html) by using template inheritance:
  #      https://docs.djangoproject.com/en/1.10/ref/templates/language/#template-inheritance
  context = {'page':page, 'notes':notes, 'bottom':bottom, 'navbar':''}
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
