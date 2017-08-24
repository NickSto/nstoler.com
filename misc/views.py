from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from myadmin.lib import require_admin_and_privacy
import collections
import subprocess
import os


@require_admin_and_privacy
def export(request):
  db_name = settings.DATABASES['default']['NAME']
  command = ['pg_dump', '-d', db_name, '-E', 'UTF-8', '-Z', '5']
  with open(os.devnull, 'w') as devnull:
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=devnull)
    response = HttpResponse(content_type='application/gzip')
    response['Content-Disposition'] = 'attachment; filename="database.sql.gz"'
    for line in process.stdout:
      response.write(line)
  return response


@require_admin_and_privacy
def env(request):
  text = ''
  for key in sorted(request.META.keys()):
    if key not in os.environ:
      text += '{}:\t{}\n'.format(key, request.META[key])
  return HttpResponse(text, content_type='text/plain; charset=UTF-8')


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
  return HttpResponse(text, content_type='text/plain; charset=UTF-8')


@require_admin_and_privacy
def setcookie(request):
  context = {'default_name':'visitors_v1', 'default_value':request.COOKIES['visitors_v1']}
  return render(request, 'misc/setcookie.tmpl', context)
