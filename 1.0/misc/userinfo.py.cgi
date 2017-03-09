#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
import os
import sys
import Cookie

COOKIE_NAME = 'visitors_v1'

#TODO: Will have to do all the Traffic.pm stuff at the top to set cookies and add the visit to the
#      database. (not worth it?)

def main(argv):
  #TODO: Make all strings u'')
  print('Content-type: text/plain; charset=utf-8\n')
  ip = os.environ.get('REMOTE_ADDR', '')
  referrer = os.environ.get('HTTP_REFERER', '')
  user_agent = os.environ.get('HTTP_USER_AGENT', '')
  cookie = get_cookie(COOKIE_NAME)
  print_info(ip, referrer, cookie, user_agent)


def get_cookie(cookie_name):
  cookie = Cookie.SimpleCookie()
  cookie.load(os.environ.get('HTTP_COOKIE', ''))
  morsel = cookie.get(cookie_name)
  if morsel:
    return morsel.coded_value
  else:
    return ''


def print_info(ip, referrer, cookie, user_agent):
  print('your IP address: ' + ip)
  print('referrer: ' + referrer)
  print('cookie: ' + cookie)
  print('user-agent string: ' + user_agent)


if __name__ == '__main__':
  sys.exit(main(sys.argv))
