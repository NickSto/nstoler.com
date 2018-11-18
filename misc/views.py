import collections
import logging
import os
import subprocess
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from myadmin.lib import require_admin_and_privacy
from utils.queryparams import QueryParams
from utils import recaptcha_verify
log = logging.getLogger(__name__)


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
  return HttpResponse(text, content_type=settings.PLAINTEXT)


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
  return HttpResponse(text, content_type=settings.PLAINTEXT)


@require_admin_and_privacy
def setcookie(request):
  context = {'default_name':'visitors_v1', 'default_value':request.COOKIES['visitors_v1']}
  return render(request, 'misc/setcookie.tmpl', context)


def dataurl(request):
  return render(request, 'misc/dataurl.tmpl')


def sessionrecover(request):
  return render(request, 'misc/sessionrecover.tmpl')


def captcha(request, name):
  context = {'name':name, 'show_captcha':True}
  if name == 'email':
    context['title'] = 'Show email:'
    context['body'] = "Sorry, I have to put it behind a CAPTCHA to keep spammers from getting it."
  else:
    context['title'] = 'Error'
    context['body'] = 'Invalid data name.'
    context['show_captcha'] = False
  return render(request, 'misc/captcha.tmpl', context)


def captchasubmit(request, name):
  params = request.POST
  context = {'name':name, 'show_captcha':False}
  if name == 'email':
    context['title'] = 'Show email:'
    context['body'] = settings.CONTACT_EMAIL
  else:
    context['title'] = 'Error'
    context['body'] = 'Invalid data name.'
    return render(request, 'misc/captcha.tmpl', context)
  response = params.get('g-recaptcha-response')
  if not recaptcha_verify(response):
    context['body'] = 'Invalid CAPTCHA response or problem verifying it!'
  return render(request, 'misc/captcha.tmpl', context)
