from .models import Visit, Visitor, User
import logging
import string
import random

#TODO: Grab info about the IP address at the time. Stuff like the ISP, ASN, and geoip data.
#      That stuff can change, especially as IPv4 addresses are bought and sold increasingly.
#      Maybe run a daemon separate from Django to do it in the background, to not hold up the
#      response. Possible data sources:
#      http://ipinfo.io/developers (ASN, geiop)
#      https://stat.ripe.net/docs/data_api (semi-official, but ASN only)

ALPHABET1 = string.ascii_lowercase + string.ascii_uppercase + string.digits + '+-'
COOKIE_EXPIRATION = 10*365*24*60*60  # 10 years


def make_cookie1():
  # Make a legacy visitors_v1 cookie:
  # 16 random characters chosen from my own base64-like alphabet I chose long ago.
  return ''.join([random.choice(ALPHABET1) for i in range(16)])


def get_or_make_cookies(request):
  cookie1 = request.COOKIES.get('visitors_v1')
  cookie2 = request.COOKIES.get('visitors_v2')
  if not cookie1:
    cookie1 = make_cookie1()
  return (cookie1, cookie2)


def set_cookies(response, cookies):
  cookie1, cookie2 = cookies
  response.set_cookie('visitors_v1', cookie1, max_age=COOKIE_EXPIRATION)
  # Don't need to set visitors_v2, since Nginx takes care of that.
  return response


def add_visit(request, response, side_effects=None):
  cookies = get_or_make_cookies(request)
  response = set_cookies(response, cookies)
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
  # Let the caller get the visitor and/or visit objects we just created.
  # If we were to return these values directly instead of through this side effect, we couldn't
  # use the quick idiom of
  #   return add_visit(request, render(request, 'notepad/notes.tmpl', context))
  if side_effects is not None:
    if 'visitor' in side_effects:
      side_effects['visitor'] = visitor
    if 'visit' in side_effects:
      side_effects['visit'] = visit
  return response


def get_or_create_visitor(ip, cookies, user_agent):
  cookies = normalize_cookies(cookies)
  visitor, user, label = get_visitor_and_user(ip, cookies, user_agent)
  if not user:
    user = User()
    user.save()
  if not visitor:
    visitor = Visitor(
      ip=ip,
      user_agent=user_agent,
      cookie1=cookies[0],
      cookie2=cookies[1],
      label=label,
      user=user
    )
    visitor.save()
  return visitor


def normalize_cookies(cookies):
  if len(cookies) == 0:
    cookie1 = None
    cookie2 = None
  elif len(cookies) == 1:
    cookie1 = cookies[0]
    cookie2 = None
  elif len(cookies) >= 2:
    cookie1 = cookies[0]
    cookie2 = cookies[1]
  return (cookie1, cookie2)


def get_visitor_and_user(ip, cookies, user_agent):
  """Look for an existing Visitor matching the current one."""
  cookie1, cookie2 = cookies
  if cookie1 is None and user_agent is None:
    logging.info('No cookie or user_agent. We must create a new Visitor.')
    return None, None, ''
  try:
    # An exact match?
    visitor = Visitor.objects.get(ip=ip, cookie1=cookie1, user_agent=user_agent)
    logging.info('This Visitor already exists (id {}).'.format(visitor.id))
    return visitor, visitor.user, visitor.label
  except Visitor.MultipleObjectsReturned:
    # Multiple matches? I'm not sure how, but just pick the first one, then.
    #TODO: Determine more intelligently which visitor to use.
    logging.warn('Multiple visitors found with ip "{}", cookie1 "{}", and user_agent "{}".'
                  .format(ip, cookie1, user_agent))
    visitor = Visitor.objects.filter(ip=ip, cookie1=cookie1, user_agent=user_agent)[0]
    return visitor, visitor.user, visitor.label
  except Visitor.DoesNotExist:
    # If no exact match, use the cookie to look for similar Visitors.
    if cookie1 is None:
      logging.info('No cookie and no match for (ip, user_agent). We must create a new Visitor.')
      return None, None, ''
    visitors = Visitor.objects.filter(cookie1=cookie1)
    if visitors:
      # Take the label for the new visitor from the existing ones.
      label = get_common_start([visitor.label for visitor in visitors])
      user = visitors[0].user
      logging.info('This Visitor does not exist, but one with the same cookie does (visitor id {}, '
                   'user id {}).'.format(visitors[0].id, user.id))
      return None, user, label
    logging.info('This Visitor does not exist, and no Visitors with this cookie have been seen '
                 'before. Creating a new one..')
    return None, None, ''


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
