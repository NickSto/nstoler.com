from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.template.defaultfilters import escape
from django.urls import reverse
from django.template import TemplateDoesNotExist
from django.db import transaction, DatabaseError
import logging
import os
from utils.queryparams import QueryParams
from myadmin.lib import is_admin_and_secure, require_admin_and_privacy
from notepad.models import Note, Page
from notepad.views import DISPLAY_ORDER_MARGIN
from .templatetags.markdown import parse_markdown
from .models import Item, ListItem, Move
log = logging.getLogger(__name__)

EDITPAGES_NAMESPACE = '__editpages__'
ITEM_TYPES = {'item':Item, 'listitem':ListItem}


##### Views #####

def view(request, page):
  params = request.GET
  is_admin = is_admin_and_secure(request)
  editing = False
  if params.get('editing'):
    if is_admin:
      editing = True
    else:
      return HttpResponseRedirect(get_view_url(page))
  context = {'editing':editing, 'editing_text':False, 'admin':is_admin}
  return show_page(request, page, context)


@require_admin_and_privacy
def edititemform(request, page):
  params = QueryParams()
  params.add('key')
  params.add('id', type=int)
  params.add('type', choices=('item', 'listitem'))
  params.add('display-type')
  params.parse(request.POST)
  log.info('Composing edit form for item: key {!r}, id {!r}'.format(params['key'], params['id']))
  item_type = ITEM_TYPES.get(params['type'])
  if not item_type:
    log.error('Invalid type {!r}.'.format(request.POST.get('type')))
    return HttpResponseRedirect(get_view_url(page))
  item = get_by_key_or_id(item_type, page, params['key'], params['id'])
  if item is None:
    log.info('No item found. Using a dummy.')
    item = {'id':params['id'], 'key':params['key'], 'note':{'content':''}}
  # Determine whether the item has a title, body, or neither.
  display_type = 'title-body'
  if params['display-type']:
    display_type = params['display-type']
  elif params['key']:
    display_type_key = params['key']+'-display-type'
    if params.get(display_type_key) is not None:
      display_type = params[display_type_key]
  context = {'editing':True, 'editing_text':True, 'editing_item':True, 'admin':True, 'item':item,
             'display_type':display_type, 'type':params['type']}
  return show_page(request, page, context)


@require_admin_and_privacy
def edititem(request, page):
  params = QueryParams()
  params.add('key')
  params.add('id', type=int)
  params.add('type', choices=('item', 'listitem'))
  params.add('content')
  params.add('title')
  params.add('body')
  params.add('attributes')
  params.parse(request.POST)
  log.info('Editing item: key {!r}, id {!r}'.format(params['key'], params['id']))
  item_type = ITEM_TYPES.get(params['type'])
  if not item_type:
    log.error('Invalid type {!r}.'.format(request.POST.get('type')))
    return HttpResponseRedirect(get_view_url(page))
  item = get_by_key_or_id(item_type, page, params['key'], params['id'])
  content = compose_content(params['title'], params['body'], params['content'])
  if item:
    log.info('Editing existing item.')
    edit_item(item, content, params['attributes'], request.visit)
  elif params['type'] == 'item':
    # Won't work for ListItems, but they can't be created via edititem anyway.
    log.info('Creating new item.')
    create_item(item_type, page, content, params['attributes'], request.visit, key=params['key'])
  else:
    log.error('Warning: Cannot edit nonexistent ListItem.')
  return HttpResponseRedirect(get_view_url(page))


@require_admin_and_privacy
def deleteitemform(request, page):
  params = QueryParams()
  params.add('type', choices=('item', 'listitem'))
  params.add('key')
  params.add('id', type=int)
  params.parse(request.POST)
  item_type = ITEM_TYPES.get(params['type'])
  if not item_type:
    log.error('Invalid type {!r}.'.format(request.POST.get('type')))
    return HttpResponseRedirect(get_view_url(page))
  item = get_by_key_or_id(item_type, page, params['key'], params['id'])
  context = {'editing':True, 'deleting_text':True, 'item':item, 'type':params['type']}
  return show_page(request, page, context)


@require_admin_and_privacy
def deleteitem(request, page):
  params = QueryParams()
  params.add('type', choices=('item', 'listitem'))
  params.add('key')
  params.add('id', type=int)
  params.parse(request.POST)
  item_type = ITEM_TYPES.get(params['type'])
  if not item_type:
    log.error('Invalid type {!r}.'.format(request.POST.get('type')))
    return HttpResponseRedirect(get_view_url(page))
  item = get_by_key_or_id(item_type, page, params['key'], params['id'])
  item.deleted = True
  item.deleting_visit = request.visit
  item.note.deleted = True
  item.note.deleting_visit = request.visit
  item.save()
  item.note.save()
  return HttpResponseRedirect(get_view_url(page))


@require_admin_and_privacy
def additem(request, page):
  params = QueryParams()
  params.add('type', choices=('item', 'listitem'))
  params.add('title')
  params.add('body')
  params.add('content')
  params.add('attributes')
  params.add('key')
  params.add('parent_key')
  params.add('parent_id', type=int)
  params.parse(request.POST)
  item_type = ITEM_TYPES.get(params['type'])
  if not item_type:
    log.error('Invalid type {!r}.'.format(request.POST.get('type')))
    return HttpResponseRedirect(get_view_url(page))
  content = compose_content(params['title'], params['body'], params['content'])
  parent_list = get_by_key_or_id(item_type, page, params['parent_key'], params['parent_id'])
  create_item(item_type, page, content, params['attributes'], request.visit, key=params['key'],
              parent_list=parent_list)
  return HttpResponseRedirect(get_view_url(page))

@require_admin_and_privacy
def moveitem(request, page):
  params = QueryParams()
  params.add('action', choices=('moveup', 'movedown'))
  params.add('type', choices=('item', 'listitem'))
  params.add('key')
  params.add('id', type=int)
  params.parse(request.POST)
  if params['type'] != 'listitem':
    log.error('Invalid type {!r}.'.format(request.POST.get('type')))
    return HttpResponseRedirect(get_view_url(page))
  item_type = ITEM_TYPES.get(params['type'])
  item = get_by_key_or_id(item_type, page, params['key'], params['id'])
  if not item:
    log.error('No item found by key {!r} or id {}.'.format(params['key'], params['id']))
    return HttpResponseRedirect(get_view_url(page))
  if item.parent:
    siblings = item.parent.sorted_items()
  else:
    log.info('Item has no parent. Using root lists.')
    siblings = get_root_lists(page)
  if params['action'] == 'movedown':
    siblings = reversed(siblings)
  last_item = None
  for this_item in siblings:
    if this_item == item and last_item is not None:
      this_move = Move(
        type='position',
        item=this_item,
        old_display_order=this_item.display_order,
        new_display_order=last_item.display_order,
        visit=request.visit,
      )
      last_move = Move(
        type='position',
        item=last_item,
        old_display_order=last_item.display_order,
        new_display_order=this_item.display_order,
        visit=request.visit,
      )
      this_item.display_order = this_move.new_display_order
      last_item.display_order = last_move.new_display_order
      try:
        with transaction.atomic():
          this_item.save()
          this_move.save()
          last_item.save()
          last_move.save()
      except DatabaseError as dbe:
        log.error('Error on saving moves: {}'.format(dbe))
      break
    last_item = this_item
  return HttpResponseRedirect(get_view_url(page))


##### Functions #####

def show_page(request, page, context):
  added_context = {'editing':False, 'editing_text':False, 'deleting_text':False, 'admin':False}
  added_context['items'] = get_items(page)
  added_context['root_lists'] = get_root_lists(page)
  for key, value in added_context.items():
    if key not in context:
      context[key] = value
  #TODO: Sanitize `page`?
  try:
    return render(request, 'editpages/{}.tmpl'.format(page), context)
  except TemplateDoesNotExist:
    return HttpResponseNotFound('Invalid page name {!r}.'.format(page), content_type=settings.PLAINTEXT)


def get_by_key_or_id(obj_type, page, key, id):
  if key:
    try:
      return obj_type.objects.get(page=page, key=key)
    except obj_type.DoesNotExist:
      log.error('{} not found by key {!r}'.format(obj_type.__name__, key))
  elif id:
    try:
      return obj_type.objects.get(page=page, pk=id)
    except obj_type.DoesNotExist:
      log.error('{} not found by id {}'.format(obj_type.__name__, id))
  return None


def get_items(page):
  items = {}
  for item in Item.objects.filter(page=page):
    if not item.note:
      log.error('Found Item with missing note! Key: {!r}.'.format(item.key))
      continue
    if item.note.deleted:
      continue
    if hasattr(item, 'deleted') and item.deleted:
      continue
    if item.key:
      # Is there already something with that key?
      if item.key in items:
        # Items take precedence over ListItems. Don't overwrite an Item with a ListItem.
        if isinstance(items[item.key], ListItem):
          continue
      items[item.key] = item
  return items


def get_root_lists(page):
  return ListItem.objects.filter(page=page, parent=None, deleted=False).order_by('display_order')


def get_view_url(page, editing=True):
  if editing:
    query_str = '?editing=true'
  else:
    query_str = ''
  if editing:
    return reverse('editpages:view', args=(page,))+query_str
  else:
    return reverse('editpages_{}'.format(page))


def compose_content(title, body, content):
  if content is None:
    content = ''
    if title is not None:
      content = '# '+title+'\n'
    if body is not None:
      content += body
  return content


def get_or_create_page(editpages_page):
  notepad_page = EDITPAGES_NAMESPACE+'/'+editpages_page
  page, created = Page.objects.get_or_create(name=notepad_page)
  return page


def edit_item(item, content, attributes, visit):
  if content != item.note.content:
    item.note = edit_note(item.note, content, visit)
  if attributes:
    if item.attributes:
      if attributes != item.attributes.content:
        item.attributes = edit_note(item.attributes, attributes, visit)
    else:
      item.attributes = create_note(item.note.page, attributes, visit)
  item.save()


def edit_note(note, new_content, visit):
  last_version = note
  last_version.deleted = True
  last_version.deleting_visit = visit
  note = Note(
    page=last_version.page,
    content=new_content,
    display_order=last_version.display_order,
    protected=last_version.protected,
    visit=visit
  )
  try:
    with transaction.atomic():
      last_version.save()
      note.save()
  except DatabaseError as dbe:
    log.error('Error on saving edited note: {}'.format(dbe))
    raise
  return note


def create_item(item_type, page_name, content, attributes, visit, key=None, parent_list=None):
  page = get_or_create_page(page_name)
  note = create_note(page, content, visit)
  if attributes:
    attr_note = create_note(page, attributes, visit)
  else:
    attr_note = None
  item = item_type(
    page=os.path.basename(page.name),
    note=note,
    attributes=attr_note
  )
  if key:
    item.key = key
  if item_type is ListItem:
    item.display_order = 1
  if parent_list:
    item.parent = parent_list
  log.info('About to save new {} (key {!r}), with content {!r}.'
           .format(item_type.__name__, item.key, note.content[:30]))
  item.save()
  if item_type is ListItem:
    item.display_order = item.id * DISPLAY_ORDER_MARGIN
    item.save()


def create_note(page, content, visit):
  note = Note(
    page=page,
    content=content,
    visit=visit,
    protected=True,
    display_order=1
  )
  note.save()
  note.display_order = note.id * DISPLAY_ORDER_MARGIN
  note.save()
  return note
