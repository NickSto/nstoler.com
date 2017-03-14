#!/usr/bin/env python3
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import sys
import errno
import logging
import argparse
import http.cookies
import urllib.parse
from datetime import datetime
import pytz
import django
import django.conf

COOKIE1_NAME = 'visitors_v1'
COOKIE2_NAME = 'visitors_v2'
ARG_DEFAULTS = {'site':'mysite', 'ignore_via':('html','css'), 'log':sys.stderr, 'volume':logging.ERROR,
                'ignore_ua':('Pingdom.com_bot_version','Functional Tester')}
DESCRIPTION = """"""
# tail -n 0 --follow=name traffic1.log 2>/dev/null | ./watch_nginx.py

def make_argparser():

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**ARG_DEFAULTS)

  parser.add_argument('-v', '--ignore-via',
    help='Ignore requests with a "via" query string parameter matching any of these values. '
         'This is a system to filter out requests for resources included in the HTML of pages, '
         'not initiated directly by the user. Give as a comma-delimited list. Default: %(default)s')
  parser.add_argument('-u', '--ignore-ua',
    help='Ignore requests from user agent strings which begin with any of these strings. Give as a '
         'comma-delimited list. Default: %(default)s')
  parser.add_argument('-S', '--site',
    help='Django project name. Default: %(default)s')
  parser.add_argument('-l', '--log', type=argparse.FileType('w'),
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  parser.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL)
  parser.add_argument('-V', '--verbose', dest='volume', action='store_const', const=logging.INFO)
  parser.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)

  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  init_logging(args.log, args.volume)

  init_django(args.site)

  list_args = process_list_args(args, ('ignore_via', 'ignore_ua'))

  watch(**list_args)


def init_logging(log_stream, log_level):
  logging.basicConfig(stream=log_stream, level=log_level, format='%(message)s')
  tone_down_logger()


def init_django(site):
  # Fix the path to be the Django BASE_DIR so it can import the site correctly.
  sys.path[0] = os.path.dirname(sys.path[0])
  os.environ['DJANGO_SETTINGS_MODULE'] = site+'.settings'
  django.setup()


def process_list_args(args, list_args):
  """Parse all the arguments which are given as comma-delimited lists, and return tuples."""
  processed_values = {}
  for list_arg in list_args:
    arg_value = getattr(args, list_arg)
    if arg_value:
      if isinstance(arg_value, tuple):
        # The default value is already a tuple, so we can just add it.
        processed_values[list_arg] = arg_value
      else:
        # If the user gave a list, it's a comma-delimited string.
        arg_value_list = arg_value.split(',')
        processed_values[list_arg] = tuple(arg_value_list)
    else:
      # If the user gave an empty string, it should be parsed as an empty tuple.
      processed_values[list_arg] = ()
  return processed_values


def watch(ignore_via=(), ignore_ua=()):
  logging.debug('Called watch(ignore_via={}, ignore_ua={})'
                .format(repr(ignore_via), repr(ignore_ua)))
  from traffic.models import Visit, Visitor, User
  import traffic.lib

  for line in sys.stdin:
    fields = parse_log_line(line)
    if fields:
      (timestamp, ip, method, scheme, host, path, query_str, referrer, user_agent, cookies,
       nginx_path, handler) = fields
    else:
      continue
    # Skip requests that weren't served directly by Nginx.
    if handler != 'nginx':
      logging.info('Ignoring request already handled by '+handler)
      continue
    # Skip requests for resources via certain sources.
    query = urllib.parse.parse_qs(query_str)
    via = query.get('via', ('',))[0]
    if via in ignore_via:
      logging.info('Ignoring request with via='+via)
      continue
    # Skip requests by certain user agents.
    ignore = False
    for ua in ignore_ua:
      if user_agent and user_agent.startswith(ua):
        ignore = True
        break
    if ignore:
      logging.info('Ignoring request from user agent "{}"'.format(user_agent))
      continue
    # Get the Visitor matching these identifiers or create one.
    visitor = traffic.lib.get_or_create_visitor(ip, cookies, user_agent)
    # Create this Visit and save it.
    visit = Visit(
      timestamp=datetime.fromtimestamp(timestamp, tz=pytz.utc),
      method=method,
      scheme=scheme,
      host=host,
      path=path,
      query_str=query_str,
      referrer=referrer,
      visitor=visitor
    )
    visit.save()
    logging.info('Created visit {}.'.format(visit.id))


def parse_log_line(line_raw):
    """Fields, as their nginx variable names:
    msec, remote_addr, request_method, scheme, http_host, request_uri, uri, args, http_referer,
    status, bytes_sent, http_user_agent, http_cookie"""
    line = line_raw.rstrip('\r\n')
    logging.debug(line)
    fields = line.split('\t')
    if len(fields) != 14:
      logging.warn('Invalid number of fields in log line. Expected 14, got {}:\n{}'
                   .format(len(fields), line))
      return None
    # Replace '-' with the appropriate null value for the field.
    for i, field in enumerate(fields):
      if field == '-':
        if i == 8 or i == 11:
           # referrer and user_agent fields
          fields[i] = None
        else:
          fields[i] = ''
    (timestamp, ip, method, scheme, host, full_path, nginx_path, nginx_query_str, referrer, code,
     size, user_agent, cookies, handler) = fields
    # Timestamp
    try:
      timestamp = float(timestamp)
    except ValueError:
      logging.warn('Invalid (non-float) timestamp: "{}".'.format(timestamp))
      return None
    # HTTP response code
    try:
      code = int(code)
    except ValueError:
      if code != '':
        logging.warn('Non-integer, non-"-" HTTP response code: "{}".'.format(code))
    # Cookies
    cookie1 = get_cookie(cookies, COOKIE1_NAME)
    cookie2 = get_cookie(cookies, COOKIE2_NAME)
    cookies = (cookie1, cookie2)
    # Path, query string.
    fields = urllib.parse.urlparse(full_path)
    path = fields[2]
    params = fields[3]
    query_str = fields[4]
    if params:
      path += ';'+params
    return (timestamp, ip, method, scheme, host, path, query_str, referrer, user_agent, cookies,
            nginx_path, handler)


def get_cookie(cookie_line, cookie_name=COOKIE1_NAME):
  parser = http.cookies.SimpleCookie()
  try:
    parser.load(cookie_line)
  except http.cookies.CookieError:
    return None
  cookie = parser.get(cookie_name)
  if cookie:
    return cookie.value
  else:
    return None


def tone_down_logger():
  """Change the logging level names from all-caps to capitalized lowercase.
  E.g. "WARNING" -> "Warning" (turn down the volume a bit in your log files)"""
  for level in (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG):
    level_name = logging.getLevelName(level)
    logging.addLevelName(level, level_name.capitalize())


def fail(message):
  logging.critical(message)
  if __name__ == '__main__':
    sys.exit(1)
  else:
    raise Exception('Unrecoverable error')


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except IOError as ioe:
    if ioe.errno != errno.EPIPE:
      raise
