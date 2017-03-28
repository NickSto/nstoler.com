from django.conf import settings
from .models import Visit, Visitor, User
import functools
import string
import random
import base64
import struct
import socket
import logging
log = logging.getLogger(__name__)

#TODO: Grab info about the IP address at the time. Stuff like the ISP, ASN, and geoip data.
#      That stuff can change, especially as IPv4 addresses are bought and sold increasingly.
#      Maybe run a daemon separate from Django to do it in the background, to not hold up the
#      response. Possible data sources:
#      http://ipinfo.io/developers (ASN, geiop)
#      https://stat.ripe.net/docs/data_api (semi-official, but ASN only)

ALPHABET1 = string.ascii_lowercase + string.ascii_uppercase + string.digits + '+-'
COOKIE_EXPIRATION = 10*365*24*60*60  # 10 years


# Decorator.
def add_visit(view):
  """Wrap a view with a function that logs the visit."""
  #TODO: This might be better written as middleware, but I'll have to look into it.
  @functools.wraps(view)
  def wrapped_view(request, *nargs, **kwargs):
    todo_cookies, visit = add_visit_get_todo_cookies(request)
    response = view(request, *nargs, **kwargs)
    return set_todo_cookies(todo_cookies, response)
  return wrapped_view


# Decorator.
def add_and_get_visit(view):
  """Wrap a view with a function that logs the visit and provides it as an argument to the view."""
  #TODO: This might be better written as middleware, but I'll have to look into it.
  @functools.wraps(view)
  def wrapped_view(request, *nargs, **kwargs):
    todo_cookies, visit = add_visit_get_todo_cookies(request)
    response = view(request, visit, *nargs, **kwargs)
    return set_todo_cookies(todo_cookies, response)
  return wrapped_view


def make_cookie1():
  # Make a legacy visitors_v1 cookie:
  # 16 random characters chosen from my own base64-like alphabet I chose long ago.
  return ''.join([random.choice(ALPHABET1) for i in range(16)])


def get_cookies(request):
  cookie1 = request.COOKIES.get('visitors_v1')
  cookie2 = request.COOKIES.get('visitors_v2')
  return (cookie1, cookie2)


def add_visit_get_todo_cookies(request):
  cookies = get_cookies(request)
  headers = request.META
  ip = headers.get('REMOTE_ADDR')
  user_agent = headers.get('HTTP_USER_AGENT')
  visitor = get_or_create_visitor(ip, cookies, user_agent)
  visit = Visit(
    method=request.method,
    scheme=request.scheme,
    host=request.get_host(),
    path=request.path_info,
    query_str=request.META.get('QUERY_STRING') or request.GET.urlencode(),
    referrer=headers.get('HTTP_REFERER'),
    visitor=visitor
  )
  visit.save()
  if cookies[0] is None and visitor.cookie1 is not None:
    todo_cookies = {'visitors_v1':visitor.cookie1}
  else:
    todo_cookies = {}
  return todo_cookies, visit


def set_todo_cookies(todo_cookies, response):
  for cookie_name, cookie_value in todo_cookies.items():
    log.info('Setting {} to {!r}.'.format(cookie_name, cookie_value))
    response.set_cookie(cookie_name, cookie_value, max_age=COOKIE_EXPIRATION)
  return response


def get_or_create_visitor(ip, cookies, user_agent, make_cookies=True):
  cookie1, cookie2 = cookies
  visitor, user, label = get_visitor_user_label(ip, user_agent, cookie1, cookie2)
  if not user:
    user = User()
    user.save()
    log.info('Created new User (id {})'.format(user.id))
  if visitor:
    # Fill in the cookie1 or cookie2 field on the Visitor if it's blank.
    # This effectively corrects data already recorded, in case the Visitor didn't receive both
    # cookies on the previous visit. This can happen if the Visitor's first visit was to a static
    # page, getting Nginx's cookie2 but no cookie1 from Django. But since this is rewriting history,
    # be very careful: only do this if the other cookie is present, meaning we can be sure enough
    # we've identified the same Visitor.
    if visitor.cookie1 is None and visitor.cookie2 is not None:
      if cookie1 is None and make_cookies:
        cookie1 = make_cookie1()
        log.info('Saw a repeat Visitor with a visitors_v2 of {!r} but no visitors_v1. Assigning '
                 '{!r}..'.format(visitor.cookie2, cookie1))
      if cookie1 is not None:
        visitor.cookie1 = cookie1
        visitor.save()
    elif visitor.cookie2 is None and visitor.cookie1 is not None and cookie2 is not None:
      #TODO: Obtain the cookie2 that Nginx set in its response, if possible.
      log.info('Saw a repeat Visitor with a visitors_v1 of {!r} but no visitors_v2. Assigning '
               '{!r}..'.format(visitor.cookie1, cookie2))
      visitor.cookie2 = cookie2
      visitor.save()
  else:
    if cookie1 is None and make_cookies:
      cookie1 = make_cookie1()
      log.info('Created a new visitors_v1 ({!r}) for a new Visitor.'.format(cookie1))
    #TODO: Obtain the cookie2 that Nginx set in its response, if possible.
    visitor = Visitor(
      ip=ip,
      user_agent=user_agent,
      cookie1=cookie1,
      cookie2=cookie2,
      label=label,
      user=user
    )
    visitor.save()
    log.info('Created a new Visitor (id {}).'.format(visitor.id))
  return visitor


def get_visitor_user_label(ip, user_agent, cookie1, cookie2):
  """Look for an existing Visitor matching the current one."""
  # Does this Visitor already exist?
  visitor = get_exact_visitor(ip, user_agent, cookie1, cookie2)
  if visitor is None:
    # If no exact match, use the cookie(s) to look for similar Visitors.
    visitors = get_visitors_by_cookie(cookie1, cookie2)
    if visitors:
      # Take the label for the new visitor from the existing ones.
      labels = [visitor.label for visitor in visitors]
      label = get_common_start(labels)
      ellipsis = ', ...'
      if len(labels) <= 5:
        ellipsis = ''
      log.info('Using the label {!r}, derived from existing label(s): "{}"{}'
               .format(label, '", "'.join(labels[:5]), ellipsis))
      return None, visitors[0].user, label
    else:
      return None, None, ''
  else:
    return visitor, visitor.user, visitor.label


def get_exact_visitor(ip, user_agent, cookie1, cookie2):
  """Get a Visitor by exact match."""
  log.info('Searching for an exact match for ip: {!r}, visitors_v1: {!r}, visitors_v2: {!r}, and '
           'user_agent: {!r}..'.format(ip, cookie1, cookie2, user_agent))
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


def get_visitors_by_cookie(cookie1, cookie2):
  log.info('Searching for an inexact match for visitors_v1: {!r} or visitors_v2: {!r}.'
           .format(cookie1, cookie2))
  visitors = None
  if cookie1 is not None:
    visitors = Visitor.objects.filter(cookie1=cookie1)
    if visitors:
      log.info('Found {} Visitor(s) with visitors_v1 == {!r}'.format(len(visitors), cookie1))
  if cookie2 is not None and not visitors:
    visitors = Visitor.objects.filter(cookie2=cookie2)
    if visitors:
      log.info('Found {} Visitor(s) with visitors_v2 == {!r}'.format(len(visitors), cookie2))
  if not visitors:
    log.info('Found no Visitor with either cookie.')
  return visitors


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


# Bot detection:
#TODO: Put these in the database for more flexibility and possibly even a gain in speed.
# These names occur in a known location in the user_agent string: After "compatible; " and before
# "/" or ";", e.g.: Mozilla/5.0 (compatible; Exabot/3.0; +http://www.exabot.com/go/robot)
UA_BOT_NAMES = ('Googlebot', 'bingbot', 'Baiduspider', 'YandexBot', 'AhrefsBot', 'Yahoo! Slurp',
                'Exabot', 'Uptimebot', 'MJ12bot', 'Yeti', 'SeznamBot', 'DotBot', 'spbot', 'Ezooms',
                'BLEXBot', 'SiteExplorer', 'SEOkicks-Robot', 'WBSearchBot', 'SemrushBot',
                'SMTBot', 'Dataprovider.com', 'SISTRIX Crawler', 'coccocbot-web')
# These names occur after "compatible; " and before " ". It's incompatible with the above, which
# allows spaces in the names.
UA_BOT_NAMES_SPACE_DELIM = ('archive.org_bot',)
# For these, the user_agent string begins with the bot name, followed by a "/".
UA_BOT_STARTSWITH = ('curl', 'Sogou web spider', 'TurnitinBot', 'Wotbox', 'SeznamBot', 'Aboundex',
                     'msnbot-media', 'masscan')


def is_robot(visit):
  visitor = visit.visitor
  if not (visit.host or visit.query_str or visit.referrer or visitor.user_agent or visitor.cookie1
          or visitor.cookie2) and (visit.path == '/' or visit.path == ''):
    return True
  elif invalid_host(visit.host):
    return True
  else:
    return is_robot_ua(visitor.user_agent)


def invalid_host(host):
  """Check every level of subdomains to allow things like "www.nstoler.com" to match "nstoler.com".
  """
  domain = ''
  for subdomain in reversed(host.split('.')):
    if domain:
      domain = subdomain + '.' + domain
    else:
      domain = subdomain
    if domain in settings.ALLOWED_HOSTS:
      return False
  return True


def is_robot_ua(user_agent):
  if user_agent is None or user_agent == '':
    return True
  # Does the user_agent contain a known bot name in the standard position?
  ua_halves = user_agent.split('compatible; ')
  if len(ua_halves) >= 2:
    # Look for it after 'compatible; ' and before '/', ';', or whitespace.
    bot_name = ua_halves[1].split('/')[0].split(';')[0]
    if bot_name in UA_BOT_NAMES:
      return True
    # Check for bot names that contain whitespace (same as above, but don't split on whitespace)
    bot_name = bot_name.split()[0]
    if bot_name in UA_BOT_NAMES_SPACE_DELIM:
      return True
  # Does the user_agent start with a known bot name?
  fields = user_agent.split('/')
  if fields[0] in UA_BOT_STARTSWITH:
    return True
  # It's not a known bot.
  return False