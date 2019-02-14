from django.conf import settings
from django.http import HttpResponse
import functools
from .models import AdminCookie


# Decorator.
def require_admin_and_privacy(view):
  """Wrap a view with a function which checks that the user is an admin connecting over HTTPS
  (or REQUIRE_HTTPS is False). If so, run the view. Otherwise, return an error page."""
  @functools.wraps(view)
  def wrapped_view(request, *nargs, **kwargs):
    admin_cookie = get_admin_cookie(request)
    if admin_cookie and (request.is_secure() or not settings.REQUIRE_HTTPS):
      return view(request, *nargs, **kwargs)
    else:
      text = 'Error: This page is restricted to the admin over HTTPS.'
      return HttpResponse(text, status=401, content_type='text/plain; charset=UTF-8')
  return wrapped_view


def get_admin_cookie(request):
  cookie = request.COOKIES.get('visitors_v1')
  if cookie:
    try:
      return AdminCookie.objects.get(cookie=cookie)
    except AdminCookie.DoesNotExist:
      pass
  return None


def is_admin_and_secure(request):
  admin_cookie = get_admin_cookie(request)
  secure_connection = request.is_secure() or not settings.REQUIRE_HTTPS
  return admin_cookie and secure_connection
