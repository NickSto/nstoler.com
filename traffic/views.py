from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotAllowed, StreamingHttpResponse
from django.urls import reverse
from django.utils.html import escape
from django.db import DataError
import django.core.paginator
from myadmin.lib import is_admin_and_secure, require_admin_and_privacy
from utils import QueryParams, boolish
from .models import Visit, IpInfo
from . import categorize
from .ipinfo import set_timezone
import collections
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

def monitor(request):
  # The query string parameters and their defaults.
  params = QueryParams()
  params.add('p', default=1, type=int)
  params.add('perpage', default=PER_PAGE_DEFAULT, type=int)
  params.add('include_me', default=False, type=boolish)
  params.add('bot_thres', default=None, type=int)
  params.add('user', type=int, default=None)
  params.parse(request.GET)
  admin = is_admin_and_secure(request)
  # Non-admins can only view their own traffic.
  if not admin:
    this_user = request.visit.visitor.user.id
    if params['user']:
      # If they gave a user, but it's not themselves, redirect back to themself.
      if params['user'] != this_user:
        return HttpResponseRedirect(reverse('traffic_monitor')+str(params.but_with('user', None)))
    else:
      # If they gave no user, that's fine. Silently show only themself.
      params['user'] = this_user
      params.params['user'].default = this_user
  # If they gave an invalid page number, redirect back to 1.
  if params['p'] < 1:
    return HttpResponseRedirect(reverse('traffic_monitor')+str(params.but_with('p', 1)))
  # Obtain visits list from database.
  if params['user'] is not None:
    visits = Visit.objects.filter(visitor__user__id=params['user'])
  elif params['include_me']:
    visits = Visit.objects.all()
  else:
    visits = Visit.objects.exclude(visitor__user__id=1)
  # Exclude robots, if requested.
  if params['bot_thres'] is not None and params['user'] is None:
    visits = visits.filter(visitor__bot_score__lt=params['bot_thres'])
  # Order by id.
  visits = visits.order_by('-id')
  # Create a Paginator.
  pages = django.core.paginator.Paginator(visits, params['perpage'])
  try:
    page = pages.page(params['p'])
  except django.core.paginator.EmptyPage:
    return HttpResponseRedirect(reverse('traffic_monitor')+str(params.but_with('p', pages.num_pages)))
  # Construct the navigation links.
  links = collections.OrderedDict()
  if page.has_previous():
    links['Earlier'] = str(params.but_with('p', page.previous_page_number()))
  if admin:
    if params['include_me']:
      links['Hide me'] = str(params.but_with('include_me', None))
    else:
      links['Include me'] = str(params.but_with('include_me', True))
    if params['bot_thres'] is not None and params['bot_thres'] != 0:
      links['Show all'] = str(params.but_with('bot_thres', None))
    if params['bot_thres'] is None or params['bot_thres'] > categorize.SCORES['bot_in_ua']:
      links['Hide robots'] = str(params.but_with('bot_thres', categorize.SCORES['bot_in_ua']))
    if params['bot_thres'] is None or params['bot_thres'] > categorize.SCORES['sent_cookies']+1:
      links['Show humans'] = str(params.but_with('bot_thres', categorize.SCORES['sent_cookies']+1))
  if page.has_next():
    links['Later'] = str(params.but_with('p', page.next_page_number()))
  context = {
    'visits': page,
    'admin':admin,
    'links': links,
    'timezone': set_timezone(request),  # Set and retrieve timezone.
    'ua_exact_thres': categorize.SCORES['ua_exact'],
    'referrer_exact_thres': categorize.SCORES['referrer_exact'],
  }
  return render(request, 'traffic/monitor.tmpl', context)


@require_admin_and_privacy
def mark_robot(request):
  if request.method != 'POST':
    return HttpResponseNotAllowed(['POST'])
  # Get query parameters.
  params = request.POST
  user_agent = params.get('user_agent')
  referrer = params.get('referrer')
  if not (user_agent or referrer):
    return HttpResponseBadRequest('Error: You must supply a user_agent and/or referrer.',
                                  content_type=settings.PLAINTEXT)
  # Do the actual marking.
  marked = categorize.mark_robot(user_agent, referrer)
  # Generate response.
  our_referrer = request.META.get('HTTP_REFERER')
  html = '<p>{} visitors marked as robots.</p>'.format(marked)
  if our_referrer:
    html += '\n<p><a href="{}">back</a></p>'.format(escape(our_referrer))
  return HttpResponse(html)


@require_admin_and_privacy
def mark_all_robots(request):
  if request.method != 'POST':
    return HttpResponseNotAllowed(['POST'])
  return StreamingHttpResponse(mark_all_robots_incremental(), content_type=settings.PLAINTEXT)


def mark_all_robots_incremental(batch_size=1000):
  """Mark all robots in batches, reporting progress along the way.
  batch_size is how many Visits at a time to process."""
  likely_bots = 0
  likely_humans = 0
  total_visits = Visit.objects.count()
  for start in range(0, total_visits+1, batch_size):
    end = start+batch_size
    bots, humans = categorize.mark_all_robots(start=start, end=end)
    likely_bots += bots
    likely_humans += humans
    status = 'Finished marking visits {} to {} ({} bots, {} humans)'.format(start, end, bots, humans)
    yield status+'\n'
    log.info(status)
  result = '{} likely bots found, {} likely humans found'.format(likely_bots, likely_humans)
  yield result
  log.info('mark_all_robots() finished. '+result)


def view_ip(request, ip=None):
  if ip is None:
    ip = request.visit.visitor.ip
  # Only allow regular users to view their own IP address.
  if is_admin_and_secure(request):
    admin = True
  else:
    ip = request.visit.visitor.ip
  # Get query parameters.
  params = request.GET
  format = params.get('format', 'html')
  # Get the IpInfos for the IP address.
  query = IpInfo.objects.filter(ip=ip).order_by('-timestamp')
  fields = ('timestamp', 'version', 'asn', 'isp', 'hostname', 'timezone', 'latitude', 'longitude',
            'country', 'region', 'town', 'zip', 'label')
  if format == 'plain':
    if not query:
      return HttpResponse('No data on ip '+ip, content_type=settings.PLAINTEXT)
    response = HttpResponse(content_type=settings.PLAINTEXT)
    response.write(ip+':\n')
    response.write('\t'.join(fields)+'\n')
    for ipinfo in query:
      values = [str(getattr(ipinfo, field, None)) for field in fields]
      response.write('\t'.join(values)+'\n')
    return response
  else:
    ipinfos = []
    try:
      last_ipinfo = None
      for ipinfo in query:
        if last_ipinfo is None:
          ipinfos.append(ipinfo)
        else:
          changed = False
          for field in fields:
            new_value = getattr(ipinfo, field, None)
            old_value = getattr(last_ipinfo, field, None)
            if field != 'timestamp' and new_value != old_value:
              changed = True
          if changed:
            ipinfos.append(ipinfo)
        last_ipinfo = ipinfo
    except DataError:
      # DataError is thrown on executing the query on an invalid ip address.
      log.warning('DataError on IP address'+ip)
      ipinfos = []
    context = {
      'ip':ip,
      'admin':admin,
      'timezone': set_timezone(request),  # Set and retrieve timezone.
      'ipinfos': ipinfos
    }
    return render(request, 'traffic/ips.tmpl', context)
