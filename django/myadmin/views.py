from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.urls import reverse
from .models import AdminCookie, AdminDigest
from .lib import get_admin_cookie
from traffic.lib import add_visit
import binascii
import hashlib

ALGORITHM = 'pbkdf2_hmac'
HASH = 'sha256'
ITERATIONS = 1000000

"""
Note: This "authentication" system is different from most.
First, it's not taken that seriously. It's a personal site no one cares much about. Still, I'm
trying to do a decent job at my first authentication system. So I'm using PBKDF2 with SHA-256 and
a high iteration count, and allowing for the algorithm to change in the future.
Second, it's just intended to identify a given visitor as the administrator or not. So there is
really only one "user". Thus there is not even a "Users" table, just a passwords table. Multiple
valid passwords are allowed. When given a password, I'd like be able to digest it and query the
passwords table directly with the result, instead of checking it against every entry. This means
I can't generate a random salt and store it with each digest. Instead, I have a global salt, so it
doesn't offer great protection. I may re-evaluate this trade-off later.
"""
#TODO: Mark visitors_v1 HTTPS only, or use a different, HTTPS-only cookie.
#TODO: Add a sub-navigation bar to go between login, logout, and hash generation.

def auth_form(request, action):
  result = request.GET.get('result')
  if result:
    return _display_result(request, action, result)
  # Only allow the form to be loaded and submitted over HTTPS.
  if settings.REQUIRE_HTTPS and not request.is_secure():
    back_link = 'https://'+request.get_host()+reverse('myadmin:auth_form', args=['login'])
    context = {
      'title': 'Access denied',
      'message': 'Access to this area is restricted to HTTPS only',
      'back_text': 'Go back',
      'back_link': back_link,
    }
    return add_visit(request, render(request, 'myadmin/auth_result.tmpl', context))
  elif action == 'hash':
    context = {
      'title':'Get password hash',
      'instruction':'Get the hash of a password:',
      'action':'hash',
      'get_password':True,
    }
  elif action == 'logout':
    context = {
      'title':'Admin logout',
      'instruction':'De-authenticate yourself as an administrator:',
      'action':'logout',
      'get_password':False,
    }
  else:
    context = {
      'title':'Admin login',
      'instruction':'Identify yourself as an administrator:',
      'action':'login',
      'get_password':True,
    }
  return add_visit(request, render(request, 'myadmin/auth_form.tmpl', context))

def submit(request, action):
  if action == 'login':
    return _submit_login(request)
  elif action == 'logout':
    return _submit_logout(request)
  elif action == 'hash':
    return _submit_hash(request)

def _submit_login(request):
  password = request.POST['password']
  digest = _get_hash(password)
  try:
    AdminDigest.objects.get(
      algorithm=ALGORITHM,
      hash=HASH,
      iterations=ITERATIONS,
      salt=settings.ADMIN_SALT,
      digest=digest
    )
    authenticated = True
  except AdminDigest.DoesNotExist:
    authenticated = False
  if authenticated:
    admin_cookie = get_admin_cookie(request)
    # Is this user already authorized? Then don't create another AdminCookie.
    if admin_cookie:
      result = 'redundant'
    else:
      cookie = request.COOKIES.get('visitors_v1')
      if cookie:
        admin_cookie = AdminCookie(cookie=cookie)
        admin_cookie.save()
        result = 'success'
      else:
        result = 'nocookie'
  else:
    result = 'badpass'
  path = reverse('myadmin:auth_form', args=('login',))
  path += '?result='+result
  return add_visit(request, HttpResponseRedirect(path))

def _submit_logout(request):
  admin_cookie = get_admin_cookie(request)
  if admin_cookie:
    admin_cookie.delete()
    result = 'success'
  else:
    result = 'redundant'
  path = reverse('myadmin:auth_form', args=('logout',))
  path += '?result='+result
  return add_visit(request, HttpResponseRedirect(path))

def _submit_hash(request):
  password = request.POST['password']
  admin_cookie = get_admin_cookie(request)
  if not (admin_cookie and (request.is_secure() or not settings.REQUIRE_HTTPS)):
    authorized = True
  else:
    authorized = False
  digest = str(_get_hash(password), 'utf8')
  text = ('{}\n\nAlgorithm:\t{}\nHash:\t\t{}\nIterations:\t{}'
          .format(digest, ALGORITHM, HASH, ITERATIONS))
  # Only give out the salt to the admin user over HTTPS.
  if authorized:
    text += '\nSalt:\t\t'+settings.ADMIN_SALT
  # Safe to return a response directly to this POST instead of redirecting because it doesn't
  # actually change anything on the server. We're just using a POST because it's potentially
  # sensitive data so we don't want it in the query url as a query string.
  return add_visit(request, HttpResponse(text, content_type='text/plain; charset=UTF-8'))

def _get_hash(password):
  pwd_bytes = bytes(password, 'utf8')
  salt = bytes(settings.ADMIN_SALT, 'utf8')
  #TODO: Replace with a function that doesn't lock process (GIL) and is faster: the docs mention
  #      this is about 3x slower than the OpenSSL version:
  #      https://docs.python.org/3.5/library/hashlib.html
  digest = hashlib.pbkdf2_hmac(HASH, pwd_bytes, salt, ITERATIONS)
  return binascii.hexlify(digest)

def _display_result(request, action, result):
  if action == 'login':
    if result == 'success':
      context = {
        'title': 'Success!',
        'message': 'Your cookie is now marked with admin privileges.',
        'back_text': 'Go back',
      }
    elif result == 'badpass':
      context = {
        'title':' Authentication failed',
        'message': 'Wrong Password',
        'back_text': 'Try again',
      }
    elif result == 'nocookie':
      context = {
        'title': 'Error',
        'message': 'Error: No cookie present!',
        'back_text': 'Try again',
      }
    elif result == 'redundant':
      context = {
        'title': 'Already authenticated',
        'message': 'You seem to already be authenticated!',
        'back_text': 'Go back',
      }
    context['back_link'] = reverse('myadmin:auth_form', args=('login',))
  elif action == 'logout':
    if result == 'success':
      context = {
        'title': 'De-authorized',
        'message': 'Cookie successfully de-authorized.',
        'back_text': 'Go back',
      }
    elif result == 'redundant':
      context = {
        'title': 'Logged out',
        'message': ('You seem to be already de-authorized: your cookie was not found in the '
                    'AdminCookie table.'),
        'back_text': 'Try again',
      }
    context['back_link'] = reverse('myadmin:auth_form', args=('logout',))
  return add_visit(request, render(request, 'myadmin/auth_result.tmpl', context))
