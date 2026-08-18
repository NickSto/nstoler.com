import collections
import logging
import os
import subprocess
import urllib.parse
import requests
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound, JsonResponse
from django.conf import settings
from myadmin.lib import require_admin_and_privacy
from utils import recaptcha_verify
from longurl import longurl
log = logging.getLogger(__name__)

# Restrictions on the redirect-resolving feature, since it makes the server fetch a
# user-supplied url (a server-side request forgery risk if left unrestricted).
RESOLVE_MAX_REDIRECTS = 20
RESOLVE_TIMEOUT = 5  # seconds, per request in the chain.
RESOLVE_MAX_RESPONSE_KB = 64  # How much of each response body to scan for a meta refresh.


#TODO: Switch to xz with https://docs.python.org/3/library/lzma.html
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
  params = request.GET
  if params.get('format') == 'plain':
    text = '\n'.join(['{}:\t{!r}'.format(key, value) for key, value in info.items()])
    return HttpResponse(text, content_type=settings.PLAINTEXT)
  else:
    data = []
    for key, value in info.items():
      data.append({'key':key, 'value':value})
    return render(request, 'misc/userinfo.tmpl', {'data':data})


@require_admin_and_privacy
def setcookie(request):
  context = {'default_name':'visitors_v1', 'default_value':request.COOKIES['visitors_v1']}
  return render(request, 'misc/setcookie.tmpl', context)


def urlparse(request):
  # Prefill the original url box from the `url` query parameter, if given.
  context = {'url': request.GET.get('url', '')}
  return render(request, 'misc/urlparse.tmpl', context)


@require_admin_and_privacy
def resolve_redirects(request):
  """Follow a url's chain of redirects (HTTP-level and <meta> refreshes) and return the final url.
  Restricted to the admin, since this makes the server fetch an arbitrary, user-supplied url
  (a server-side request forgery risk)."""
  url = request.GET.get('url', '').strip()
  if not url:
    return JsonResponse({'error': 'No url given.'}, status=400)
  if urllib.parse.urlsplit(url).scheme not in ('http', 'https'):
    return JsonResponse({'error': 'Only http and https urls are supported.'}, status=400)
  hops = []
  try:
    for reply in longurl.follow_redirects(
        url,max_redirects=RESOLVE_MAX_REDIRECTS, max_response=RESOLVE_MAX_RESPONSE_KB,
        timeout=RESOLVE_TIMEOUT,
      ):
      hops.append({'url':reply.url, 'type':reply.type, 'code':reply.code, 'location':reply.location})
  except (requests.exceptions.RequestException, longurl.URLError) as error:
    return JsonResponse({'error': f'Error following redirects: {error}'}, status=502)
  if hops:
    final_url = hops[-1]['location']
  else:
    final_url = url
  return JsonResponse({'final_url': final_url, 'hops': hops})


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


def journalurl(request, proxy, url):
  # `proxy` is the domain of the proxy server, e.g. libraries.psu.edu.
  if url.startswith('http://'):
    url_trimmed = url[7:]
  elif url.startswith('https://'):
    url_trimmed = url[8:]
  elif url.startswith('http:/'):
    url_trimmed = url[6:]
  elif url.startswith('https:/'):
    url_trimmed = url[7:]
  else:
    return HttpResponseNotFound('Invalid url: no http:/. Saw:\n'+url, content_type=settings.PLAINTEXT)
  fields = url_trimmed.split('/')
  if len(fields) < 2:
    return HttpResponseNotFound('Invalid url: no path. Saw:\n'+url, content_type=settings.PLAINTEXT)
  domain = fields[0].replace('.', '-')
  path = '/'+'/'.join(fields[1:])
  new_url = 'https://'+domain+'.ezaccess.'+proxy+path
  return HttpResponseRedirect(new_url)
