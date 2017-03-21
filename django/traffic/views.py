from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.urls import reverse
from django.conf import settings
from .lib import add_visit, is_robot
from .models import Visit
from myadmin.lib import get_admin_cookie
import logging
log = logging.getLogger(__name__)

PER_PAGE_DEFAULT = 50

def monitor_redirect(request):
  """Redirect to the monitor() view, preserving the query string."""
  path = reverse('traffic:monitor')
  query_string = request.META.get('QUERY_STRING') or request.GET.urlencode()
  if query_string:
    path += '?'+query_string
  return add_visit(request, redirect(path, permanent=True))

#TODO: A view to set a Visitor.label or Visitor.is_me, so I can do it via a link in the monitor.
#TODO: Let any user see the monitor, but restrict to their own visits.
#      Generalize "include=me" to apply to any user, and only allow an admin to see all users.

def monitor(request):
  # Only allow access to admin users over HTTPS.
  admin_cookie = get_admin_cookie(request)
  if not (admin_cookie and (request.is_secure() or not settings.REQUIRE_HTTPS)):
    text = 'This page is only for admin users visiting via HTTPS.'
    return add_visit(request, HttpResponse(text, content_type='text/plain; charset=UTF-8'))
  # Get query parameters.
  params = request.GET
  page = int(params.get('p', 1))
  per_page = int(params.get('per_page', PER_PAGE_DEFAULT))
  include = params.get('include')
  hide = params.get('hide')
  if page < 1:
    page = 1
  # Calculate start and end of visits to request.
  if include == 'me':
    total_visits = Visit.objects.count()
  else:
    total_visits = Visit.objects.exclude(visitor__user__id=1).count()
  start = (page-1)*per_page + 1
  end = page*per_page
  # Is this page beyond the last possible one?
  if page*per_page - total_visits >= per_page:
    # Then redirect to the last possible page.
    new_page = (total_visits-1) // per_page + 1
    return add_visit(request, redirect(_construct_monitor_path(new_page, include, hide, per_page)))
  # Obtain visits list from database.
  if include == 'me':
    visits_unbounded = Visit.objects.order_by('-id')[start:]
  else:
    visits_unbounded = Visit.objects.exclude(visitor__user__id=1).order_by('-id')[start:]
  # Exclude robots, if requested.
  if hide == 'robots':
    visits = []
    for visit in visits_unbounded:
      if not is_robot(visit):
        visits.append(visit)
      if len(visits) >= per_page:
        break
  else:
    visits = visits_unbounded[:per_page]
  # Calculate some data for the template.
  if include:
    include_param = '&include='+include
  else:
    include_param = ''
  if hide:
    hide_param = '&hide='+hide
  else:
    hide_param = ''
  if total_visits > end:
    next_page = page+1
  else:
    next_page = None
  context = {
    'current': page,
    'prev': page-1,
    'next': next_page,
    'start': start,
    'end': end,
    'include_param': include_param,
    'hide_param': hide_param,
    # 'debug': debug,
    'visits': visits,
  }
  return add_visit(request, render(request, 'traffic/monitor.tmpl', context))


def _construct_monitor_path(page, include, hide, per_page):
  #TODO: Use a different solution instead of re-building the prettified query string.
  path = reverse('traffic:monitor')
  if page > 1:
    path += '?p='+str(page)
  if include == 'me':
    path += '&include=me'
  if hide == 'robots':
    path += '&hide=robots'
  if per_page != PER_PAGE_DEFAULT:
    path += '&per_page='+str(per_page)
  return path
