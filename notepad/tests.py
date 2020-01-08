from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from .models import Note, Page
from traffic.models import Visit

TEST_PAGE = 'xwasebwnav'
TEST_CONTENT = 'rsjhlsvoda'
# From https://mathiasbynens.be/notes/javascript-unicode#poo-test
# The first 20 symbols are in the range from U+0000 to U+00FF, then one between U+0100 and U+FFFF,
# and finally a non-BMP astral symbol between U+010000 and U+10FFFF.
UNICODE_CONTENT = 'Iñtërnâtiônàlizætiøn☃💩'

def add_note(page_name, content, deleted=False, visit=None):
  try:
    page = Page.objects.get(name=page_name)
  except Page.DoesNotExist:
    page = Page(name=page_name)
    page.save()
  note = Note(page=page, content=content, deleted=deleted, visit=visit)
  note.save()
  return note


# Generic test functions for re-using with different input data.

def test_view_note(tester, page, content):
  add_note(page, content)
  response = tester.client.get(reverse('notepad:view', args=(page,)))
  tester.assertEqual(response.status_code, 200)
  tester.assertContains(response, content)
  notes = response.context['notes']
  tester.assertEqual(len(notes), 1)
  if len(notes) > 0:
    for note_tuple in notes:
      tester.assertEqual(len(note_tuple), 2)
      if len(note_tuple) == 2:
        note, lines = note_tuple
        tester.assertEqual(lines, [content])

def test_add_note(tester, page, content):
  path = reverse('notepad:add', args=(page,))
  post_data = {'page':page, settings.HONEYPOT_NAME:'', 'content':content}
  response = tester.client.post(path, post_data)
  location = reverse('notepad:view', args=(page,))
  tester.assertEqual(response.get('Location'), location+'#bottom')
  tester.assertEqual(response.status_code, 302)
  notes = Note.objects.all()
  tester.assertEqual(len(notes), 1)
  if len(notes) > 0:
    note = notes[0]
    tester.assertEqual(note.content, content)
    tester.assertEqual(note.page.name, page)

def test_delete_note(tester, page, content):
  note = add_note(page, content)
  tester.assertEqual(Note.objects.count(), 1)
  path = reverse('notepad:delete', args=(page,))
  post_data = {'page':page, settings.HONEYPOT_NAME:'', 'note_'+str(note.id):'on'}
  response = tester.client.post(path, post_data)
  location = reverse('notepad:view', args=(page,))
  tester.assertEqual(response.get('Location'), location+'#bottom')
  tester.assertEqual(response.status_code, 302)
  try:
    note = Note.objects.get(pk=note.id)
    missing = False
  except Note.DoesNotExist:
    missing = True
  tester.assertEqual(missing, False)
  if not missing:
    tester.assertEqual(note.page.name, page)
    tester.assertEqual(note.content, content)
    tester.assertEqual(note.deleted, True)


class NoteDisplayTests(TestCase):

  def test_empty_page(self):
    response = self.client.get(reverse('notepad:view', args=(TEST_PAGE,)))
    self.assertEqual(response.status_code, 200)
    self.assertContains(response, 'Nothing here yet')
    self.assertEqual(response.context['notes'], [])

  def test_one_note(self):
    test_view_note(self, TEST_PAGE, TEST_CONTENT)

  def test_unicode_note(self):
    test_view_note(self, UNICODE_CONTENT, UNICODE_CONTENT)

  #TODO: Test hiding/showing deleted notes.


class NoteAddTests(TestCase):

  def test_add_one_note(self):
    test_add_note(self, TEST_PAGE, TEST_CONTENT)

  def test_add_unicode_note(self):
    test_add_note(self, UNICODE_CONTENT, UNICODE_CONTENT)


class NoteDeleteTests(TestCase):

  def test_delete_one_note(self):
    test_delete_note(self, TEST_PAGE, TEST_CONTENT)

  def test_delete_unicode_note(self):
    test_delete_note(self, UNICODE_CONTENT, UNICODE_CONTENT)


#TODO: Move these to traffic.tests.
class NoteTrafficTests(TestCase):

  def test_add_first_visit(self):
    user_agent = 'tester'
    page_url = reverse('notepad:view', args=(TEST_PAGE,))
    response = self.client.get(page_url, HTTP_USER_AGENT=user_agent)
    cookie1 = response.cookies.get('visitors_v1')
    self.assertIsNotNone(cookie1)
    visits = Visit.objects.all()
    self.assertEqual(len(visits), 1)
    if len(visits) > 0:
      visit = visits[0]
      self.assertEqual(visit.path, page_url)
      self.assertEqual(visit.visitor.user_agent, user_agent)
      self.assertEqual(visit.visitor.cookie1, cookie1.value)
      # visitors_v2 is only added by Nginx, which is not running in the test.
      # In any case, it would have to be added later by watch_nginx.py.
      self.assertIsNone(visit.visitor.cookie2)

  def test_add_visit(self):
    user_agent = 'tester'
    cookie1 = 'zkZsrdMr8HdooDda'
    cookie2 = 'isXNNVjX6+U+5CtqAwVZAg=='
    cookie_header = 'visitors_v1='+cookie1+'; visitors_v2='+cookie2
    page_url = reverse('notepad:view', args=(TEST_PAGE,))
    self.client.get(page_url, HTTP_COOKIE=cookie_header, HTTP_USER_AGENT=user_agent)
    visits = Visit.objects.all()
    self.assertEqual(len(visits), 1)
    if len(visits) > 0:
      visit = visits[0]
      self.assertEqual(visit.path, page_url)
      self.assertEqual(visit.visitor.cookie1, cookie1)
      self.assertEqual(visit.visitor.cookie2, cookie2)
      self.assertEqual(visit.visitor.user_agent, user_agent)
