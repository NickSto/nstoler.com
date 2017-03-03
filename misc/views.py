from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from myadmin.lib import get_admin_cookie
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
  return HttpResponse(text, content_type='text/plain; charset=UTF-8')
