from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.urls import reverse
from django.template.defaultfilters import escape, urlize
import re
from myadmin.lib import is_admin_and_secure, require_admin_and_privacy
from .models import Item, List, ListItem


##### Views ######

def view(request, page):
  params = request.GET
  is_admin = is_admin_and_secure(request)
  if params.get('editing'):
    if is_admin:
      editing = True
    else:
      view_url = reverse('editpages:view', args=(page,))
      return HttpResponseRedirect(view_url)
  items = get_items()
  lists = get_lists()
  context = {'items':items, 'lists':lists, 'editing':editing, 'editing_item':False, 'admin':is_admin}
  if page == 'home':
    return render(request, 'editpages/home.tmpl', context)
  else:
    return HttpResponseNotFound('Invalid page name {!r}.'.format(page), content_type=settings.PLAINTEXT)


##### Functions #####

def get_items():
  item_objs = Item.objects.all()
  items = {}
  for item_obj in item_objs:
    if item_obj.note.deleted:
      continue
    item = parse_content(item_obj.note.content)
    if not item:
      continue
    item['id'] = item_obj.id
    items[item_obj.key] = item
  return items


def get_lists():
  list_objs = List.objects.filter(deleted=False).order_by('display_order')
  lists = []
  for list_obj in list_objs:
    title = parse_markdown(escape(list_obj.title.note.content))
    list_dict = {'id':list_obj.id, 'title':title, 'items':[]}
    for item_obj in sorted(list_obj.items, key=lambda item: item.display_order):
      if item_obj.deleted:
        continue
      item = parse_content(item_obj.note.content)
      if not item:
        continue
      item['id'] = item_obj.id
      list_dict['items'].append(item)
    lists.append(list_dict)
  return lists


def parse_content(content):
  item = {'title':'', 'body':''}
  lines = content.splitlines()
  if not lines:
    return None
  if lines[0].startswith('#'):
    item['title'] = parse_markdown(escape(lines[0].lstrip('#').strip()))
    lines = lines[1:]
  item['body'] = parse_markdown(escape('\n'.join(lines)))
  return item


def parse_markdown(markdown, span_lines=False):
  """Parse a small subset of Markdown: italics/bold, and links.
  italics are only recognized with the * syntax, bold with **.
  links are only recognized in the form of [title](url)."""
  #TODO: Just use the Markdown package.
  #      py-gfm can get it close to Github syntax: https://pypi.python.org/pypi/py-gfm
  if span_lines:
    lines = [markdown]
  else:
    lines = markdown.splitlines()
  html_lines = []
  for line in lines:
    html = parse_links(line)
    html = parse_style(html, '**', 'strong')
    html = parse_style(html, '*', 'em')
    html_lines.append(html)
  return '\n'.join(html_lines)


def parse_links(markdown):
  return re.sub(r'\[([^]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', markdown)


def parse_style(markdown, delim='**', tag='strong'):
  html = ''
  fields = markdown.split(delim)
  i = 0
  while i < len(fields):
    if i < len(fields)-1 and fields[i].endswith('\\'):
      html += fields[i] + delim
      i += 1
    elif i <= len(fields)-3:
      html += '{0}<{tag}>{1}</{tag}>'.format(fields[i], fields[i+1], tag=tag)
      i += 2
    elif i == len(fields)-2:
      html += fields[i] + delim
      i += 1
    else:
      html += fields[i]
      i += 1
  return html
