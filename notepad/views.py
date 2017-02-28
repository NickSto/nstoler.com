from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render, redirect
from django.utils import timezone
from .models import Note
import traffic.lib
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
  template = loader.get_template('notepad/notes.tmpl')
  response = HttpResponse(template.render(context, request))
  response, visitor, visit = traffic.lib.add_visit(request, response)
  return response

def add(request):
  params = request.POST
  #TODO: Email warning about detected spambots.
  #TODO: Check if the notes were added to the main "notepad" page.
  response = redirect('notepad:notes', params['page'])
  response, visitor, visit = traffic.lib.add_visit(request, response)
  if params['site'] == '':
    note = Note(
      page=params['page'],
      content=params['content'],
      timestamp=timezone.now(),
      visitor=visitor
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
        note.delete()
  #TODO: Email warning about detected spambots.
  #TODO: Check if the notes were deleted from the main "notepad" page.
  response = redirect('notepad:notes', params['page'])
  response, visitor, visit = traffic.lib.add_visit(request, response)
  return response

def random(request):
  alphabet = string.ascii_lowercase
  page = ''.join([rand.choice(alphabet) for i in range(5)])
  response = redirect('notepad:notes', page)
  response, visitor, visit = traffic.lib.add_visit(request, response)
  return response
