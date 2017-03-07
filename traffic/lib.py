from .models import Visit, Visitor
import string
import random

#TODO: Grab info about the IP address at the time. Stuff like the ISP, ASN, and geoip data.
#      That stuff can change, especially as IPv4 addresses are bought and sold increasingly.
#      Maybe run a daemon separate from Django to do it in the background, to not hold up the
#      response.

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
  # Check if this visitor has already been seen.
  try:
    visitor = Visitor.objects.get(ip=ip, cookie1=cookies[0], user_agent=user_agent)
  except Visitor.MultipleObjectsReturned:
    #TODO: handle
    raise
  except Visitor.DoesNotExist:
    visitors = Visitor.objects.filter(cookie1=cookies[0])
    label = ''
    is_me = None
    for visitor in visitors:
      #TODO: Do something (log?) if there are multiple, disagreeing labels or is_me values.
      if visitor.label:
        label = visitor.label
      if visitor.is_me:
        is_me = True
    visitor = Visitor(
      ip=ip,
      user_agent=user_agent,
      cookie1=cookies[0],
      cookie2=cookies[1],
      label=label,
      is_me=is_me
    )
    visitor.save()
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
