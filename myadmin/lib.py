from .models import AdminCookie

def get_admin_cookie(request):
  cookie = request.COOKIES.get('visitors_v1')
  if cookie:
    try:
      return AdminCookie.objects.get(cookie=cookie)
    except AdminCookie.DoesNotExist:
      pass
  return None
