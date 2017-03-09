from django.test import TestCase
from django.urls import reverse
from .models import Note, Page

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
        tester.assertEqual(note.id, 1)
        tester.assertEqual(lines, [content])

def test_add_note(tester, page, content):
  path = reverse('notepad:add', args=(page,))
  post_data = {'page':page, 'site':'', 'content':content}
  response = tester.client.post(path, post_data)
  location = reverse('notepad:view', args=(page,))
  tester.assertEqual(response.get('Location'), location)
  tester.assertEqual(response.status_code, 302)
  try:
    note = Note.objects.get(pk=1)
    missing = False
  except Note.DoesNotExist:
    missing = True
  tester.assertEqual(missing, False)
  if not missing:
    tester.assertEqual(note.content, content)
    tester.assertEqual(note.page.name, page)

def test_delete_note(tester, page, content):
  add_note(page, content)
  path = reverse('notepad:delete', args=(page,))
  post_data = {'page':page, 'site':'', 'note_1':'on'}
  response = tester.client.post(path, post_data)
  location = reverse('notepad:view', args=(page,))
  tester.assertEqual(response.get('Location'), location)
  tester.assertEqual(response.status_code, 302)
  try:
    note = Note.objects.get(pk=1)
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
