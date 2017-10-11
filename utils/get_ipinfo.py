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
import django
import django.conf
assert sys.version_info.major >= 3, 'Python 3 required'

# Initialize Django and allow imports from it.
script_dir = os.path.dirname(os.path.realpath(__file__))
sys.path[0] = os.path.dirname(script_dir)
site_name = os.environ.get('SITE', 'mysite')
os.environ['DJANGO_SETTINGS_MODULE'] = site_name+'.settings'
django.setup()

# Do imports from our Django site.
from traffic.models import Visitor, IpInfo
from traffic.ipinfo import get_ip_data, make_ip_info


DESCRIPTION = """Retrieve the IpInfo for some historical visitor IP addresses which are missing it.
This will go through Visitors from latest to earliest, looking for ones with missing IpInfo. It will
try to obtain the IpInfo for each one and store it. After --limit requests to the IP metadata APIs
it will exit. So if you run this once a day (after the API limits have reset), eventually all
unknown IP addresses should be described."""


def make_argparser():
  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.add_argument('-l', '--limit', type=int, default=500,
    help='Stop after this many retrievals from the IP metadata APIs. Default: %(default)s')
  parser.add_argument('-t', '--timeout', type=int, default=10,
    help='Timeout for requests to APIs. Default: %(default)s')
  parser.add_argument('-L', '--log', type=argparse.FileType('w'), default=sys.stderr,
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  parser.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL,
    default=logging.WARNING)
  parser.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
  parser.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)
  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')
  tone_down_logger()

  requests = 0
  failures = 0
  done_ips = set()
  for visitor in Visitor.objects.order_by('-id'):
    if requests >= args.limit:
      break
    if visitor.ip in done_ips:
      continue
    if IpInfo.objects.filter(ip=visitor.ip):
      done_ips.add(visitor.ip)
      continue
    ip_data = get_ip_data(visitor.ip, timeout=args.timeout)
    requests += 1
    if ip_data:
      try:
        make_ip_info(visitor.ip, ip_data)
      except ValueError:
        fail(ip_data)
    else:
      failures += 1
      logging.info('Failed to retrieve IpInfo from API for {}'.format(visitor.ip))
    done_ips.add(visitor.ip)

  logging.info('Done IPs: {}'.format(len(done_ips)))
  logging.info('Lookup failures: {}'.format(failures))
  logging.info('Total requests: {}'.format(requests))


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
