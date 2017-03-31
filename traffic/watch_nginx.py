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
import subprocess
import http.cookies
import urllib.parse
from datetime import datetime
import pytz
import django
import django.conf

COOKIE1_NAME = 'visitors_v1'
COOKIE2_NAME = 'visitors_v2'
ARG_DEFAULTS = {'log_file':sys.stdin, 'site':'mysite', 'ignore_via':('html','css','js'),
                'volume':logging.ERROR, 'log':sys.stderr,
                'ignore_ua':('Pingdom.com_bot_version','Functional Tester')}
DESCRIPTION = """"""

def make_argparser():

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**ARG_DEFAULTS)

  parser.add_argument('log_file', metavar='path/to/traffic2.log', nargs='?',
    help='Nginx traffic log file. Omit to read from stdin.')
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

  watch(args.log_file, **list_args)


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


def watch(source, ignore_via=(), ignore_ua=()):
  logging.debug('Called watch({}, ignore_via={!r}, ignore_ua={!r})'
                .format(source, ignore_via, ignore_ua))
  import traffic.models
  import traffic.lib

  if source is not sys.stdin:
    tail_proc = subprocess.Popen(['tail', '-n', '0', '--follow=name', source],
                                 stdout=subprocess.PIPE, universal_newlines=True)
    stream = tail_proc.stdout

  for line in stream:
    fields = parse_log_line(line)
    if not fields:
      continue
    # Skip requests that weren't served directly by Nginx.
    if fields['handler'] == 'django':
      if fields['uid_set']:
        logging.info('Request served by django, but $uid_set is present. Adding this cookie to '
                     'Visit.cookies_set, since django didn\'t see it.')
        add_cookie2_to_old_visit(**fields)
      else:
        logging.info('Ignoring request already handled by {handler}.'.format(**fields))
      continue
    # Skip requests for resources via certain sources.
    query = urllib.parse.parse_qs(fields['query_str'])
    via = query.get('via', ('',))[0]
    if via in ignore_via:
      logging.info('Ignoring request with via={}.'.format(via))
      continue
    # Skip requests by certain user agents.
    ignore = False
    for ua in ignore_ua:
      if fields['user_agent'] and fields['user_agent'].startswith(ua):
        ignore = True
        break
    if ignore:
      logging.info('Ignoring request from user agent "{user_agent}"'.format(**fields))
      continue
    # Get the Visitor matching these identifiers or create one.
    main_cookies = get_cookie_values(fields['cookies'], COOKIE1_NAME, COOKIE2_NAME)
    visitor = traffic.lib.get_or_create_visitor(fields['ip'], main_cookies, fields['user_agent'])
    # Create this Visit and save it.
    visit = traffic.models.Visit(
      timestamp=datetime.fromtimestamp(fields['timestamp'], tz=pytz.utc),
      method=fields['method'],
      scheme=fields['scheme'],
      host=fields['host'],
      path=fields['path'],
      query_str=fields['query_str'],
      referrer=fields['referrer'],
      visitor=visitor
    )
    visit.save()
    # Set the cookies for the visit.
    cookies_got = create_cookies_got(fields['cookies'])
    visit.cookies_got.add(*cookies_got)
    if fields['uid_set']:
      cookie = get_cookie_from_uid(fields['uid_set'])
      if cookie:
        visit.cookies_set.add(cookie)
        logging.info('$uid_set is present. Added {}={} to the Visit.'
                     .format(cookie.name, cookie.value))
    visit.save()
    logging.info('Created visit {}.'.format(visit.id))


def parse_log_line(line_raw):
    """Fields, as their nginx variable names and the alias I use in this code:
    The numbers in the columns are how many times I've seen the value be "-" or "" in my logs.
        nginx             my name             "-"      ""
    0:  $msec             timestamp             0       0
    1:  $remote_addr      ip                    0       0
    2:  $request_method   method             8874       0
    3:  $scheme           scheme                0       0
    4:  $http_host        host              14532       6
    5:  $request_uri      full_path          8892       0
    6:  $uri              nginx_path         8874      18
    7:  $args             nginx_query_str  837480       0
    8:  $http_referer     referrer         743706      30
    9:  $status           code                  0       0
    10: $bytes_sent       size                  0       0
    11: $http_user_agent  user_agent        24577     126
    12: $http_cookie      cookies          718739     157
    13: $handler          handler               ?       ?   (a custom variable from my conf)
    14: $uid_set          uid_set               ?       ?"""
    field_names = ('timestamp', 'ip', 'method', 'scheme', 'host', 'full_path', 'nginx_path',
                   'nginx_query_str', 'referrer', 'code', 'size', 'user_agent', 'cookies_str',
                   'handler', 'uid_set')
    line = line_raw.rstrip('\r\n')
    logging.debug(line)
    field_values = line.split('\t')
    if len(field_values) != len(field_names):
      logging.warn('Invalid number of fields in log line. Expected {}, got {}:\n{}'
                   .format(len(field_names), len(field_values), line))
      return None
    # Store the values in the log entry in a dict.
    fields = {}
    for name, value in zip(field_names, field_values):
      if value == '-':
        # Replace '-' with the appropriate null value for the field.
        if value == 'referrer' or value == 'user_agent':
          fields[name] = None
        else:
          fields[name] = ''
      else:
        fields[name] = value
    # Timestamp
    try:
      fields['timestamp'] = float(fields['timestamp'])
    except ValueError:
      logging.warn('Invalid (non-float) timestamp: "{timestamp}".'.format(**fields))
      return None
    # HTTP response code
    try:
      fields['code'] = int(fields['code'])
    except ValueError:
      if fields['code'] != '':
        logging.warn('Non-integer, non-"-" HTTP response code: "{code}".'.format(**fields))
    # Cookies
    fields['cookies'] = http.cookies.SimpleCookie()
    try:
      fields['cookies'].load(fields['cookies_str'])
    except http.cookies.CookieError:
      pass
    # Path, query string.
    url_parts = urllib.parse.urlparse(fields['full_path'])
    fields['path'] = url_parts[2]
    params = url_parts[3]
    if params:
      fields['path'] += ';'+params
    fields['query_str'] = url_parts[4]
    return fields


def get_cookie_values(cookies, *cookie_names):
  cookie_values = []
  for cookie_name in cookie_names:
    if cookie_name in cookies:
      cookie_values.append(cookies.get(cookie_name).value)
    else:
      cookie_values.append(None)
  return cookie_values


def create_cookies_got(cookies):
  import traffic.lib
  cookies_got = []
  for name, morsel in cookies.items():
    cookie = traffic.lib.get_or_create_cookie('got', name, morsel.value)
    cookies_got.append(cookie)
  return cookies_got


def get_cookie_from_uid(uid):
  import traffic.lib
  cookie_name, cookie_value = parse_uid_field(uid)
  return traffic.lib.get_or_create_cookie('set', cookie_name, cookie_value)


def parse_uid_field(uid_set):
  """Parse the $uid_set field from Nginx's logs and, if valid, translate its value into the
  corresponding cookie value."""
  import traffic.lib
  fields = uid_set.split('=')
  if len(fields) != 2:
    logging.warn('Error parsing $uid_set "{}".'.format(uid_set))
    return None
  name, uid = fields
  return name, traffic.lib.encode_cookie(uid)


def add_cookie2_to_old_visit(uid_set=None, timestamp=None, ip=None, cookies=None, path=None,
                             query_str=None, referrer=None, user_agent=None, **kwargs):
  import traffic.lib
  if not (timestamp and ip and uid_set):
    return
  # Build a set of characteristics to use to find in the database the same request Nginx saw.
  selectors = {'visitor__ip':ip}
  if path:
    selectors['path'] = path
  if query_str:
    selectors['query_str'] = query_str
  if referrer:
    selectors['referrer'] = referrer
  if user_agent:
    selectors['visitor__user_agent'] = user_agent
  if cookies and COOKIE1_NAME in cookies:
    selectors['visitor__cookie1'] = cookies.get(COOKIE1_NAME).value
  visit = find_visit_by_timestamp(timestamp, selectors)
  if not visit:
    logging.warn('Looked in the traffic database but could not find the visit corresponding to the '
                 'request logged by Nginx.')
    return
  cookie2 = get_cookie_from_uid(uid_set)
  visit.cookies_set.add(cookie2)
  visit.save()
  logging.info('Successfully identified the visit corresponding to the Nginx request and added '
               'cookie {}.'.format(cookie2))
  return


def find_visit_by_timestamp(timestamp, selectors={}, tolerance=0.05, max_tries=8):
  import traffic.models
  tries = 0
  visits = ()
  while len(visits) != 1 and tries < max_tries:
    start = datetime.fromtimestamp(timestamp-tolerance, tz=pytz.utc)
    end = datetime.fromtimestamp(timestamp+tolerance, tz=pytz.utc)
    visits = traffic.models.Visit.objects.filter(timestamp__range=(start, end), **selectors)
    tries += 1
    if len(visits) == 0:
      # If we didn't find anything, widen the timestamp tolerance.
      tolerance = tolerance*2
    elif len(visits) > 1:
      # If we found too many, shorten the timestamp tolerance a little.
      tolerance = tolerance/1.25
  logging.info('Tried {} times to find a Visit corresponding to the Nginx one we saw, and found {} '
               'Visit(s).'.format(tries, len(visits)))
  if len(visits) == 1:
    visit = visits[0]
    logging.info('The timestamp difference (nginx - django) was {} sec.'
                 .format(timestamp-visit.timestamp.timestamp()))
    return visit
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
