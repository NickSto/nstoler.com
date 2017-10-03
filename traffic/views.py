from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from django.urls import reverse
from django.utils.html import escape
from django.conf import settings
from .models import Visit, Visitor, Robot
from myadmin.lib import get_admin_cookie, require_admin_and_privacy
from . import categorize
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
  bot_thres = params.get('bot_thres')
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
  # Obtain visits list from database.
  if user is not None:
    visits = Visit.objects.filter(visitor__user__id=user)
  elif include == 'me':
    visits = Visit.objects.order_by('-id')
  else:
    visits = Visit.objects.exclude(visitor__user__id=1)
  # Exclude robots, if requested.
  if bot_thres is not None and user is None:
    visits = visits.filter(visitor__bot_score__lt=bot_thres)
  total_visits = visits.count()
  start = (page-1)*per_page
  end = page*per_page
  # Is this page beyond the last possible one?
  if total_visits > 0 and page*per_page - total_visits >= per_page:
    # Then redirect to the last possible page.
    new_params['p'] = (total_visits-1) // per_page + 1
    query_str = _construct_query_str(new_params, {'user':default_user})
    return redirect(reverse('traffic_monitor')+query_str)
  # Slice the list of all visits into an ordered list of the visits for this page.
  visits = visits.order_by('-id')[start:end]
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
    link_data.append(('Later', 'p', page-1))
  if admin:
    if include == 'me':
      link_data.append(('Hide me', 'include', None))
    else:
      link_data.append(('Include me', 'include', 'me'))
  if admin:
    if bot_thres is None:
      link_data.append(('Hide robots', 'bot_thres', categorize.SCORES['bot_in_ua']))
    else:
      link_data.append(('Show robots', 'bot_thres', None))
  if total_visits > end:
    link_data.append(('Earlier', 'p', page+1))
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
  defaults = {'p':1, 'user':1, 'include':None, 'bot_thres':None, 'per_page':PER_PAGE_DEFAULT}
  defaults.update(extra_defaults)
  query_str = ''
  param_list = ['p', 'user', 'include', 'bot_thres', 'per_page']
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


@require_admin_and_privacy
def mark_all_robots(request):
  """Go through the entire database and mark robots we weren't aware of before.
  Basically re-loads robots.yaml and marks historical bots."""
  #TODO: Cache .save()s and commit them all at once using @transaction.atomic:
  #      https://stackoverflow.com/questions/3395236/aggregating-saves-in-django/3397586#3397586
  bot_strings = categorize.load_bot_strings()
  probable_bots = 0
  maybe_bots = 0
  for visitor in Visitor.objects.all():
    user_agent = visitor.user_agent
    if visitor.bot_score < categorize.SCORES['ua_contains']:
      if categorize.is_robot_ua(bot_strings, user_agent):
        visitor.bot_score = categorize.SCORES['ua_contains']
        probable_bots += 1
        visitor.save()
    if visitor.bot_score < categorize.SCORES['bot_in_ua']:
      if 'bot' in user_agent.lower():
        visitor.bot_score = categorize.SCORES['bot_in_ua']
        maybe_bots += 1
        visitor.save()
  out_text = '{} likely bots found\n{} possible bots found'.format(probable_bots, maybe_bots)
  return HttpResponse(out_text, content_type='text/plain; charset=UTF-8')


@require_admin_and_privacy
def mark_robot(request):
  # Get query parameters.
  params = request.POST
  user_agent = params.get('user_agent')
  if not user_agent:
    return HttpResponseBadRequest('Error: You must supply a user_agent.', content_type='text/plain; charset=UTF-8')
  try:
    Robot.objects.get(user_agent=user_agent, ip=None, cookie1=None, cookie2=None)
  except Robot.DoesNotExist:
    robot = Robot(user_agent=user_agent, version=2)
    robot.save()
  bot_score = categorize.SCORES['ua_exact']
  marked = Visitor.objects.filter(user_agent=user_agent, bot_score__lt=bot_score).update(bot_score=bot_score)
  referrer = request.META.get('HTTP_REFERER')
  html = '<p>{} visitors marked as robots.</p>'.format(marked)
  if referrer:
    html += '\n<p><a href="{}">back</a></p>'.format(escape(referrer))
  return HttpResponse(html)
