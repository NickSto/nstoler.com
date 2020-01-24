#!/usr/bin/env python3
import argparse
import collections
import logging
import os
import pathlib
import sys
import django
import django.conf
assert sys.version_info.major >= 3, 'Python 3 required'

# Initialize Django and allow imports from it.
script_dir = pathlib.Path(__file__).resolve().parent
sys.path[0] = str(script_dir.parent)
site_name = os.environ.get('SITE', 'mysite')
os.environ['DJANGO_SETTINGS_MODULE'] = site_name+'.settings'
django.setup()

# Do imports from our Django site.
from traffic.models import Spam, User

DESCRIPTION = """Export data from the Spam table to tsv format."""

ROW_FIELDS = (
  'timestamp', 'is_me', 'is_boring', 'captcha_version', 'captcha_failed',
  'js_enabled', 'solved_grid', 'grid_autofilled', 'honeypot_len', 'content_len',
)

Row = collections.namedtuple('Row', ROW_FIELDS)


def make_argparser():
  parser = argparse.ArgumentParser(add_help=False, description=DESCRIPTION)
  options = parser.add_argument_group('Options')
  options.add_argument('-h', '--help', action='help',
    help='Print this argument help text and exit.')
  options.add_argument('-H', '--no-header', dest='header', default=True, action='store_false',
    help="Don't print a header line. Normally prints a header line with field labels, prefixed "
      "with a '#'.")
  logs = parser.add_argument_group('Logging')
  logs.add_argument('-l', '--log', type=argparse.FileType('w'), default=sys.stderr,
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  volume = logs.add_mutually_exclusive_group()
  volume.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL,
    default=logging.WARNING)
  volume.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
  volume.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)
  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')

  me = User.objects.get(pk=1, label='me')

  if args.header:
    print('#', end='')
    print(*ROW_FIELDS, sep='\t')
  for spam in Spam.objects.all():
    row_dict = {field:getattr(spam,field) for field in ROW_FIELDS if hasattr(spam,field)}
    row_dict['timestamp'] = int(spam.visit.timestamp.timestamp())
    row_dict['is_me'] = spam.visit.visitor.user == me
    row = Row(**row_dict)
    print(*row, sep='\t')


def fail(message):
  logging.critical('Error: '+str(message))
  if __name__ == '__main__':
    sys.exit(1)
  else:
    raise Exception(message)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except BrokenPipeError:
    pass
