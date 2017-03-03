from django.test import TestCase
from django.urls import reverse
from .models import Note

TEST_PAGE = 'xwasebwnav'
TEST_CONTENT = 'rsjhlsvoda'

def add_note(page, content, deleted=False, visit=None):
  note = Note(page=page, content=content, deleted=deleted, visit=visit)
  note.save()


class NoteDisplayTests(TestCase):

  def test_empty_page(self):
    response = self.client.get(reverse('notepad:view', args=(TEST_PAGE,)))
    self.assertEqual(response.status_code, 200)
    self.assertContains(response, 'Nothing here yet')
    self.assertQuerysetEqual(response.context['notes'], [])

  def test_one_note(self):
    TEST_CONTENT = 'rsjhlsvoda'
    add_note(TEST_PAGE, TEST_CONTENT)
    response = self.client.get(reverse('notepad:view', args=(TEST_PAGE,)))
    self.assertEqual(response.status_code, 200)
    self.assertContains(response, TEST_CONTENT)
    self.assertQuerysetEqual(response.context['notes'], ["(1, ['"+TEST_CONTENT+"'])"])

  #TODO: Test hiding/showing deleted notes.


class NoteAddTests(TestCase):

  def test_add_one_note(self):
    TEST_CONTENT = 'rsjhlsvoda'
    path = reverse('notepad:add', args=(TEST_PAGE,))
    post_data = {'page':TEST_PAGE, 'site':'', 'content':TEST_CONTENT}
    response = self.client.post(path, post_data)
    location = reverse('notepad:view', args=(TEST_PAGE,))
    self.assertEqual(response.get('Location'), location)
    self.assertEqual(response.status_code, 302)
    try:
      note = Note.objects.get(pk=1)
      missing = False
    except Note.DoesNotExist:
      missing = True
    self.assertEqual(missing, False)
    if not missing:
      self.assertEqual(note.content, TEST_CONTENT)
      self.assertEqual(note.page, TEST_PAGE)


class NoteDeleteTests(TestCase):

  def test_delete_one_note(self):
    add_note(TEST_PAGE, TEST_CONTENT)
    path = reverse('notepad:delete', args=(TEST_PAGE,))
    post_data = {'page':TEST_PAGE, 'site':'', 'note_1':'on'}
    response = self.client.post(path, post_data)
    location = reverse('notepad:view', args=(TEST_PAGE,))
    self.assertEqual(response.get('Location'), location)
    self.assertEqual(response.status_code, 302)
    try:
      note = Note.objects.get(pk=1)
      missing = False
    except Note.DoesNotExist:
      missing = True
    self.assertEqual(missing, False)
    if not missing:
      self.assertEqual(note.page, TEST_PAGE)
      self.assertEqual(note.content, TEST_CONTENT)
      self.assertEqual(note.deleted, True)
