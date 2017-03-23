from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from myadmin.lib import get_admin_cookie
from traffic.lib import add_visit
import collections
import os


def env(request):
  # Only allow showing details about the server environment to the admin over HTTPS.
  admin_cookie = get_admin_cookie(request)
  if admin_cookie and (request.is_secure() or not settings.REQUIRE_HTTPS):
    text = ''
    for key in sorted(request.META.keys()):
      if key not in os.environ:
        text += '{}:\t{}\n'.format(key, request.META[key])
  else:
    text = 'Error: This page is restricted to the admin over HTTPS.'
  return add_visit(request, HttpResponse(text, content_type='text/plain; charset=UTF-8'))


def userinfo(request):
  headers = request.META
  info = collections.OrderedDict()
  info['IP address'] = headers.get('REMOTE_ADDR')
  info['User Agent'] = headers.get('HTTP_USER_AGENT')
  info['Referrer'] = headers.get('HTTP_REFERER')
  info['visitors_v1'] = request.COOKIES.get('visitors_v1')
  info['visitors_v2'] = request.COOKIES.get('visitors_v2')
  info['Cookie header'] = headers.get('HTTP_COOKIE')
  text = '\n'.join(['{}:\t{!r}'.format(key, value) for key, value in info.items()])
  return add_visit(request, HttpResponse(text, content_type='text/plain; charset=UTF-8'))


def setcookie(request):
  admin_cookie = get_admin_cookie(request)
  if admin_cookie and (request.is_secure() or not settings.REQUIRE_HTTPS):
    context = {'default_name':'visitors_v1', 'default_value':request.COOKIES['visitors_v1']}
    response = render(request, 'misc/setcookie.tmpl', context)
  else:
    text = 'Error: This page is restricted to the admin over HTTPS.'
    response = HttpResponse(text, content_type='text/plain; charset=UTF-8')
  return add_visit(request, response)
