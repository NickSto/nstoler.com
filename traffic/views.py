from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed, StreamingHttpResponse
from django.urls import reverse
from django.utils.html import escape
from django.db import DataError
from .models import Visit, IpInfo
from myadmin.lib import get_admin_cookie, require_admin_and_privacy
from . import categorize
from .ipinfo import set_timezone
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
  try:
    bot_thres = int(params.get('bot_thres'))
  except (ValueError, TypeError):
    bot_thres = None
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
    if bot_thres is not None and bot_thres != 0:
      link_data.append(('Show all', 'bot_thres', None))
    if bot_thres is None or bot_thres > categorize.SCORES['bot_in_ua']:
      link_data.append(('Hide robots', 'bot_thres', categorize.SCORES['bot_in_ua']))
    if bot_thres is None or bot_thres > categorize.SCORES['sent_cookies']+1:
      link_data.append(('Show humans', 'bot_thres', categorize.SCORES['sent_cookies']+1))
  if total_visits > end:
    link_data.append(('Earlier', 'p', page+1))
  links = _construct_links(link_data, new_params, {'user':default_user})
  context = {
    'visits': visits,
    'admin':admin,
    'start': start+1,
    'end': min(end, start+len(visits)),
    'links': links,
    'timezone': set_timezone(request),  # Set and retrieve timezone.
    'ua_exact_thres': categorize.SCORES['ua_exact'],
    'referrer_exact_thres': categorize.SCORES['referrer_exact'],
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


def view_ip(request, ip):
  # Only allow regular users to view their own IP address.
  admin_cookie = get_admin_cookie(request)
  if admin_cookie and (request.is_secure() or not settings.REQUIRE_HTTPS):
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
