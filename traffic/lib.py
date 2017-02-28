from .models import Visit, Visitor
import string
import random

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

def add_visit(request, response):
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
    host=request.get_host(),
    url=request.get_full_path(),
    referrer=headers.get('HTTP_REFERER'),
    visitor=visitor
  )
  visit.save()
  return response, visitor, visit
