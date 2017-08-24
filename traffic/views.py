from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.urls import reverse
from django.conf import settings
from .categorize import is_robot
from .models import Visit
from myadmin.lib import get_admin_cookie
import logging
log = logging.getLogger(__name__)

PER_PAGE_DEFAULT = 50

def monitor_redirect(request):
  """Redirect to the monitor() view, preserving the query string."""
  path = reverse('traffic_monitor')
  query_string = request.META.get('QUERY_STRING') or request.GET.urlencode()
  if query_string:
    path += '?'+query_string
  return redirect(path, permanent=True)

#TODO: A view to set a Visitor.label or Visitor.is_me, so I can do it via a link in the monitor.

#TODO: Clean up this mess.
def monitor(request):
  # Only allow access to admin users over HTTPS.
  this_user = request.visit.visitor.user.id
  admin_cookie = get_admin_cookie(request)
  if admin_cookie and (request.is_secure() or not settings.REQUIRE_HTTPS):
    user = None
    admin = True
  else:
    user = request.visit.visitor.user.id
    admin = False
  # Get query parameters.
  params = request.GET
  page = int(params.get('p', 1))
  per_page = int(params.get('per_page', PER_PAGE_DEFAULT))
  include = params.get('include')
  hide = params.get('hide')
  if admin and 'user' in params:
    user = int(params['user'])
  if page < 1:
    page = 1
  # Create a params dict for rendering new links.
  new_params = params.copy()
  new_params['p'] = page
  new_params['per_page'] = per_page
  if admin:
    default_user = None
  else:
    default_user = this_user
  # Calculate start and end of visits to request.
  if user is not None:
    total_visits = Visit.objects.filter(visitor__user__id=user).count()
  elif include == 'me':
    total_visits = Visit.objects.count()
  else:
    total_visits = Visit.objects.exclude(visitor__user__id=1).count()
  start = (page-1)*per_page
  end = page*per_page
  # Is this page beyond the last possible one?
  if total_visits > 0 and page*per_page - total_visits >= per_page:
    # Then redirect to the last possible page.
    new_params['p'] = (total_visits-1) // per_page + 1
    query_str = _construct_query_str(new_params, {'user':default_user})
    return redirect(reverse('traffic_monitor')+query_str)
  # Obtain visits list from database.
  if user is not None:
    visits_unbounded = Visit.objects.filter(visitor__user__id=user).order_by('-id')[start:]
  elif include == 'me':
    visits_unbounded = Visit.objects.order_by('-id')[start:]
  else:
    visits_unbounded = Visit.objects.exclude(visitor__user__id=1).order_by('-id')[start:]
  # Exclude robots, if requested.
  if hide == 'robots' and user is None:
    visits = []
    for visit in visits_unbounded:
      if not is_robot(visit):
        visits.append(visit)
      if len(visits) >= per_page:
        break
  else:
    visits = list(visits_unbounded[:per_page])
  # Add this visit to the start of the list, if it's not there but should be.
  if start == 0 and (user == this_user or (user is None and include == 'me')):
    if len(visits) == 0:
      log.info('No visits. Adding this one..')
      visits = [request.visit]
    elif visits[0].id != request.visit.id:
      log.info('Adding this visit to the start..')
      visits = [request.visit] + visits[:per_page-1]
  # Construct the navigation links.
  link_data = []
  if page > 1:
    link_data.append(('< Later', 'p', page-1))
  if admin:
    if include == 'me':
      link_data.append(('Hide me', 'include', None))
    else:
      link_data.append(('Include me', 'include', 'me'))
  if admin:
    if hide == 'robots':
      link_data.append(('Show robots', 'hide', None))
    else:
      link_data.append(('Hide robots', 'hide', 'robots'))
  if total_visits > end:
    link_data.append(('Earlier >', 'p', page+1))
  links = _construct_links(link_data, new_params, {'user':default_user})
  context = {
    'visits': visits,
    'admin':admin,
    'start': start+1,
    'end': min(end, start+len(visits)),
    'links': links,
  }
  return render(request, 'traffic/monitor.tmpl', context)


def _construct_links(link_data, params, extra_defaults):
  base = reverse('traffic_monitor')
  links = []
  for text, param, value in link_data:
    params_tmp = params.copy()
    params_tmp[param] = value
    href = base+_construct_query_str(params_tmp, extra_defaults)
    links.append((text, href))
  return links


def _construct_query_str(params, extra_defaults):
  """Construct the query string, omitting default values and with parameters in a predetermined
  order."""
  defaults = {'p':1, 'user':1, 'include':None, 'hide':None, 'per_page':PER_PAGE_DEFAULT}
  defaults.update(extra_defaults)
  query_str = ''
  param_list = ['p', 'user', 'include', 'hide', 'per_page']
  for param in params:
    if param not in param_list:
      param_list.append(param)
  for param in param_list:
    value = params.get(param)
    if value is not None and value != defaults[param]:
      if query_str:
        joiner = '&'
      else:
        joiner = '?'
      query_str += '{}{}={}'.format(joiner, param, value)
  return query_str
