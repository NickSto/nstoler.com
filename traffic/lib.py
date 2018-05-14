from django.db import connection
from .models import Visit, Visitor, User, Cookie
from .categorize import get_bot_score
from .ipinfo import ip_to_ipinfo
from utils import async
import string
import random
import base64
import struct
import socket
import logging
log = logging.getLogger(__name__)

ALPHABET1 = string.ascii_lowercase + string.ascii_uppercase + string.digits + '+-'
COOKIE_MAX_AGE = 10*365*24*60*60  # 10 years
PINGDOM_UA = 'Pingdom.com_bot_version_'


def middleware(get_response):
  """Wrap a view with a function that logs the visit.
  It also makes the Visit available as the visit property of the request."""
  def wrapper(request):
    params = request.GET
    via = params.get('via')
    if via in ('js', 'css', 'html') or skip_visit(request):
      request.visit = None
    else:
      request.visit = get_or_create_visit_and_visitor(request)
    # Send the request to the view and get the response.
    response = get_response(request)
    if request.visit is not None:
      response = set_cookies(request.visit, response)
    return response
  return wrapper


def get_or_create_visit_and_visitor(request):
  """Do the actual work of logging the visit. Return the Visit object."""
  request_data = unpack_request(request)
  visitor = get_or_create_visitor(**request_data)
  log.debug('Got or created Visitor {}.'.format(visitor.id))
  visit = create_visit(request_data, visitor, request.COOKIES)
  log.debug('Created visit {}.'.format(visit.id))
  run_background_tasks(visitor, request_data)
  return visit


@async
def run_background_tasks(visitor, request_data):
  """Execute tasks which aren't necessary to finish before the request is returned.
  Currently: Get IpInfo and the Visitor.bot_score."""
  # timeout=10 because there's no rush in a background thread.
  log.debug('Running background tasks..')
  ipinfo = ip_to_ipinfo(visitor.ip, timeout=10)
  if ipinfo:
    log.info('Success getting IpInfo for {}'.format(visitor.ip))
  else:
    log.warning('Failed getting IpInfo for {}'.format(visitor.ip))
  visitor.bot_score = get_bot_score(**request_data)
  visitor.save()
  # Have to close the new connection Django made for this thread.
  connection.close()


def get_cookies(request):
  cookie1 = request.COOKIES.get('visitors_v1')
  cookie2 = request.COOKIES.get('visitors_v2')
  return (cookie1, cookie2)


def set_cookies(visit, response):
  for cookie in visit.cookies_set.all():
    log.info('Setting {} to {!r}.'.format(cookie.name, cookie.value))
    cookie_attributes = {}
    for field in ('max_age', 'expires', 'path', 'domain', 'secure', 'httponly'):
      if hasattr(cookie, field):
        cookie_attributes[field] = getattr(cookie, field)
    response.set_cookie(cookie.name, cookie.value, **cookie_attributes)
  return response


def create_visit(request_data, visitor, request_cookies):
  visit = Visit(
    method=request_data['method'],
    scheme=request_data['scheme'],
    host=request_data['host'],
    path=request_data['path'],
    query_str=request_data['query_str'],
    referrer=request_data['referrer'],
    visitor=visitor
  )
  visit.save()
  # Take care of the cookies received and sent.
  cookies_got, cookies_set = create_cookies_got_set(request_cookies)
  visit.cookies_got.add(*cookies_got)
  visit.cookies_set.add(*cookies_set)
  visit.save()
  return visit


def create_cookies_got_set(request_cookies):
  cookies_got = []
  for name, value in request_cookies.items():
    cookies_got.append(get_or_create_cookie('got', name, value))
  if request_cookies.get('visitors_v1') is None:
    cookie1_properties = {'name':'visitors_v1', 'value':make_cookie1(), 'max_age':COOKIE_MAX_AGE}
    cookie1 = get_or_create_cookie('set', **cookie1_properties)
    cookies_set = [cookie1]
  else:
    cookies_set = []
  return cookies_got, cookies_set


def get_or_create_cookie(direction, name=None, value=None, **attributes):
  matches = Cookie.objects.filter(direction=direction, name=name, value=value, **attributes)
  if name.startswith('visitors_v'):
    attr_str = ', '.join([key+'='+str(val) for key, val in attributes.items()])
    if attr_str:
      attr_str = ' ('+attr_str+')'
  if matches:
    if name.startswith('visitors_v'):
      log.info('Found {} existing cookies matching {} cookie {}={}{}'
               .format(len(matches), direction, name, value, attr_str))
    return matches[0]
  else:
    if name.startswith('visitors_v'):
      log.info('No match for {} cookie {}={}{}'.format(direction, name, value, attr_str))
    cookie = Cookie(direction=direction, name=name, value=value, **attributes)
    cookie.save()
    return cookie


def make_cookie1():
  # Make a legacy visitors_v1 cookie:
  # 16 random characters chosen from my own base64-like alphabet I chose long ago.
  return ''.join([random.choice(ALPHABET1) for i in range(16)])


def unpack_request(request):
  headers = request.META
  cookie1, cookie2 = get_cookies(request)
  return {
    'ip': headers.get('REMOTE_ADDR'),
    'user_agent': headers.get('HTTP_USER_AGENT'),
    'cookie1': cookie1,
    'cookie2': cookie2,
    'method': request.method,
    'scheme': request.scheme,
    'host': request.get_host(),
    'path': request.path_info,
    'query_str': headers.get('QUERY_STRING') or request.GET.urlencode(),
    'referrer': headers.get('HTTP_REFERER')
  }


def skip_visit(request):
  user_agent = request.META.get('HTTP_USER_AGENT', '')
  path = request.path_info
  if user_agent.startswith(PINGDOM_UA) and path == '/':
    return True
  return False


def get_or_create_visitor(ip=None, user_agent=None, cookie1=None, cookie2=None, **kwargs):
  """Find a Visitor by ip, user_agent, and cookies sent (only visitors_v1/2).
  If no exact match for the Visitor is found, create one. In that case, if a Visitor with a matching
  cookie can be found, assume it's the same User."""
  visitor, user, label = get_visitor_user_and_label(ip, user_agent, cookie1, cookie2)
  if not user:
    user = User()
    user.save()
    log.info('Created new User (id {})'.format(user.id))
  if not visitor:
    visitor = Visitor(
      ip=ip,
      user_agent=user_agent,
      cookie1=cookie1,
      cookie2=cookie2,
      label=label,
      user=user,
      version=2,
    )
    visitor.save()
    log.info('Created a new Visitor (id {}).'.format(visitor.id))
  return visitor


def get_visitor_user_and_label(ip, user_agent, cookie1, cookie2):
  """Look for an existing Visitor matching the current one.
  Returns:
  visitor: Only an exact match (identical ip, user_agent, cookie1, and cookie2 fields).
    If multiple Visitors match, return the first one. If none match, return None.
  user: If an exact match, the User for that Visitor. If no exact match, look for Visitors with a
    matching cookie. If any are found, return the User for the first Visitor. Otherwise, return None.
  label: If an exact match, return the label for that Visitor. If no exact match, find Visitors with
    a matching cookie and return the common start of their labels. Otherwise, return an empty string.
  """
  # Does this Visitor already exist?
  visitor = get_exact_visitor(ip, user_agent, cookie1, cookie2)
  if visitor is None:
    # If no exact match, use the cookie(s) to look for similar Visitors.
    visitors = get_visitors_by_cookie((cookie1, cookie2))
    if visitors:
      user, label = pick_user_and_label(visitors)
      return None, user, label
    else:
      return None, None, ''
  else:
    return visitor, visitor.user, visitor.label


def get_exact_visitor(ip, user_agent, cookie1, cookie2):
  """Get a Visitor by exact match.
  It will find any Visitor with the same ip, user_agent, cookie1, and cookie2. If any of these are
  None, the field in the Visitor must be null too. If more than one match is found, the first will
  be returned. Returns None if no matches are found.
  Note, though, that this requires at least one cookie. Nothing will be returned otherwise."""
  log.info('Searching for an exact match for ip: {!r}, visitors_v1: {!r}, visitors_v2: {!r}, and '
           'user_agent: {!r}..'.format(ip, cookie1, cookie2, user_agent))
  if cookie1 is None and cookie2 is None:
    log.info('Both cookies are None. Can\'t get an exact match with just ip and user_agent.')
    return None
  try:
    # An exact match?
    visitor = Visitor.objects.get(ip=ip, user_agent=user_agent, cookie1=cookie1, cookie2=cookie2)
    log.info('This Visitor already exists (id {}).'.format(visitor.id))
  except Visitor.MultipleObjectsReturned:
    # Multiple matches? This shouldn't happen, but just pick the first one, then.
    #TODO: Determine more intelligently which visitor to use.
    visitor = Visitor.objects.filter(ip=ip, user_agent=user_agent, cookie1=cookie1, cookie2=cookie2)[0]
    log.warn('Multiple Visitors found. Using first one (id {})'.format(visitor.id))
  except Visitor.DoesNotExist:
    log.info('No exact match found.')
    visitor = None
  return visitor


def get_visitors_by_cookie(cookies):
  """Search for Visitors by cookie (an "inexact" match).
  First, look for Visitors where the cookie1 or cookie2 fields match, in that order. If either
  cookie is None, skip trying to match on it.
  Then try looking for Visitors with Visits where either cookie was set (in Visit.cookies_set).
  Returns a list of matching Visitors."""
  if len(cookies) == 2:
    log.info('Searching for an inexact match for visitors_v1: {!r} or visitors_v2: {!r}.'
             .format(cookies[0], cookies[1]))
  # Look for a Visitor with matching cookie1 or cookie2 fields.
  visitors = get_visitors_by_cookie_property(cookies)
  if not visitors:
    visitors = get_visitors_by_cookies_set(cookies)
  if not visitors:
    log.info('Found no Visitor with either cookie.')
  return visitors


def get_visitors_by_cookie_property(cookies):
  """Find Visitors whose cookie1 or cookie2 fields match one of the given cookies."""
  for i, cookie in enumerate(cookies):
    if cookie is not None:
      num = str(i+1)
      cookie_selector = {'cookie'+num:cookie}
      visitors = Visitor.objects.filter(**cookie_selector)
      if visitors:
        log.info('Found {} Visitor(s) with visitors_v{} == {!r}'
                 .format(len(visitors), num, cookie))
        return visitors
  return ()


def get_visitors_by_cookies_set(cookies):
  """Look for Visitors where we previously set either cookie to them in an HTTP response.
  A hit means we set the cookie on a previous visit, and now the client is sending it back to us
  (confirming that it accepted it!)."""
  for cookie in cookies:
    if cookie is not None:
      visitors = Visitor.objects.filter(visit__cookies_set__value=cookie)  #TODO: index?
      if visitors:
        log.info('Found {} Visitor(s) where the cookie {!r} was set in an HTTP response.'
                 .format(len(visitors), cookie))
        return visitors
  return ()


def pick_user_and_label(visitors):
  # Take the label for the new visitor from the existing ones.
  labels = [visitor.label for visitor in visitors]
  label = get_common_start(labels)
  ellipsis = ', ...'
  if len(labels) <= 5:
    ellipsis = ''
  log.info('Using the label {!r}, derived from existing label(s): "{}"{}'
           .format(label, '", "'.join(labels[:5]), ellipsis))
  return visitors[0].user, label


def get_common_start(labels):
  """Example: get_common_start(['me and you', 'me and you at 1507', 'me and Emily']) -> 'me and'
  Ignores empty strings (adding an empty string to the above list would give the same result).
  """
  common_start = None
  for label in labels:
    if label == '':
      continue
    elif common_start is None:
      common_start = label.split()
    else:
      label_parts = label.split()
      common_start_new = []
      for part1, part2 in zip(common_start, label_parts):
        if part1 == part2:
          common_start_new.append(part1)
      common_start = common_start_new
  if common_start is None:
    return ''
  else:
    return ' '.join(common_start)


def decode_cookie(cookie):
  """Decode an Nginx userid cookie into a uid string.
  Taken from: https://stackoverflow.com/questions/18579127/parsing-nginxs-http-userid-module-cookie-in-python/19037624#19037624
  This algorithm is for version 2 of http://wiki.nginx.org/HttpUseridModule.
  This nginx module follows the apache mod_uid module algorithm, which is
  documented here: http://www.lexa.ru/programs/mod-uid-eng.html.
  """
  # get the raw binary value
  binary_cookie = base64.b64decode(cookie)
  # unpack into 4 parts, each a network byte orderd 32 bit unsigned int
  unsigned_ints = struct.unpack('!4I', binary_cookie)
  # convert from network (big-endian) to host byte (probably little-endian) order
  host_byte_order_ints = [socket.ntohl(i) for i in unsigned_ints]
  # convert to upper case hex value
  uid = ''.join(['{0:08X}'.format(h) for h in host_byte_order_ints])
  return uid


def encode_cookie(uid):
  """Encode a uid into an Nginx userid cookie.
  Reversed from decode_cookie() above."""
  unsigned_ints = []
  if len(uid) != 32:
    return None
  for i in range(0, 32, 8):
    host_byte_str = uid[i:i+8]
    try:
      host_byte_int = int(host_byte_str, 16)
    except ValueError:
      return None
    net_byte_int = socket.htonl(host_byte_int)
    unsigned_ints.append(net_byte_int)
  binary_cookie = struct.pack('!4I', *unsigned_ints)
  cookie_bytes = base64.b64encode(binary_cookie)
  return str(cookie_bytes, 'utf8')
