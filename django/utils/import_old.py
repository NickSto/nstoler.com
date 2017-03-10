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
import configparser
import urllib.parse
from datetime import datetime
import pytz
import pymysql.cursors
import pymysql
import django
import django.conf

ARG_DEFAULTS = {'site':'mysite', 'charset':'latin1', 'host':'localhost',
                'config':'utils/dbi_config.ini', 'log':sys.stderr, 'volume':logging.ERROR}
DESCRIPTION = """"""


def make_argparser():

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**ARG_DEFAULTS)

  parser.add_argument('database', choices=('traffic', 'notepad'),
    help='Name of the database to import.')
  parser.add_argument('-s', '--save', action='store_true',
    help='Actually modify the database and perform the import. Otherwise it will not be changed.')
  parser.add_argument('-c', '--config',
    help='Config file to read for database connection parameters like username and password. '
         'Default: %(default)s')
  parser.add_argument('-S', '--site',
    help='Name of the Django site we\'re writing to. Default: %(default)s')
  parser.add_argument('-H', '--host',
    help='Hostname of the source database. Default: %(default)s')
  parser.add_argument('-u', '--user')
  parser.add_argument('-p', '--password')
  parser.add_argument('-C', '--charset',
    help='Charset of the source database. Note: The MySQL instance on DigitalOcean uses latin1. '
         'Full UTF-8 support would be "utf8mb4". You can find this with the commands '
         '"USE [database_name]; SELECT @@character_set_database, @@collation_database;". '
         'Default: %(default)s')
  parser.add_argument('-l', '--limit', type=int)
  parser.add_argument('-r', '--resume', type=int)
  parser.add_argument('-n', '--note', type=int,
    help='Just print this note.')
  parser.add_argument('-U', '--get-unicode', action='store_true',
    help='Print non-ascii notes.')
  parser.add_argument('-L', '--log', type=argparse.FileType('w'),
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  parser.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL)
  parser.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
  parser.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)

  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')
  tone_down_logger()

  script_dir = os.path.dirname(os.path.realpath(__file__))
  sys.path[0] = os.path.dirname(script_dir)

  if not (args.user and args.password):
    user, password, database = get_settings(args.config, args.database)
  else:
    user = args.user
    password = args.password
    if args.database == 'notepad':
      database = 'content'
    elif args.database == 'traffic':
      database = 'traffic'

  # django.conf.settings.configure()
  os.environ['DJANGO_SETTINGS_MODULE'] = args.site+'.settings'
  django.setup()

  connection = pymysql.connect(host=args.host,
                               user=user,
                               passwd=password,
                               db=database,
                               charset=args.charset,
                               cursorclass=pymysql.cursors.DictCursor)

  try:
    with connection.cursor() as cursor:
      if args.database == 'traffic':
        transfer_traffic(cursor, save=args.save, limit=args.limit, resume=args.resume)
      elif args.database == 'content' or args.database == 'notepad':
        transfer_notepad(cursor, save=args.save, limit=args.limit, resume=args.resume, get_note=args.note,
                         get_unicode=args.get_unicode)
  finally:
    connection.close()


def get_settings(config_file, database):
  config = configparser.RawConfigParser()
  config.read(config_file)
  if database == 'traffic':
    section = 'Tracker'
  elif database == 'notepad':
    section = 'Customizer'
  user = config.get(section, 'user')
  password = config.get(section, 'password')
  database = config.get(section, 'database')
  return user, password, database


def transfer_traffic(cursor, save=False, limit=None, resume=None):
  import traffic.models
  import traffic.lib

  query = """
    SELECT vtr.visitor_id, vtr.ip, vtr.is_me, vtr.label, vtr.cookie, vtr.user_agent,
           vt.visit_id, vt.unix_time, vt.page, vt.referrer
    FROM visitors as vtr, visits as vt
    WHERE vtr.visitor_id = vt.visitor_id
    ORDER BY vt.visit_id
  """
  total = cursor.execute(query)
  logging.info('Total visits found: '+str(total))

  rows = 0
  me = None
  users_by_cookie = {}
  users_by_label = {}
  visitor_ids = {}
  for row in cursor.fetchall():

    rows += 1
    if limit and rows > limit:
      break

    if resume:
      visit_id = row['visit_id']
      if visit_id < resume:
        continue

    logging.info('Adding visit: {visitor_id}/{visit_id} {ip}, {label}, {cookie}: {page}'.format(**row))
    # for key, value in row.items():
    #   print('{}:\t({})\t{}'.format(key, type(value).__name__, value))

    label = row['label'] or ''
    cookie = row['cookie']
    visitor_id = row['visitor_id']
    if visitor_id in visitor_ids:
      logging.debug('Visitor {} already present in visitor_ids.'.format(visitor_id))
      visitor = visitor_ids[visitor_id]
    elif save:
      logging.debug('Visitor {} is new.'.format(visitor_id))
      if row['is_me'] == '':
        is_me = True
      else:
        is_me = None
      # Get the user for this visitor.
      if is_me:
        logging.debug('  The visitor is me.')
        # If it's marked as me, we know that's one user: me.
        if me is None:
          logging.debug('    First time we\'ve seen me! Creating User..')
          me = traffic.models.User(label='me')
          me.save()
          assert me.id == 1, me.id
        user = me
      else:
        logging.debug('  The visitor isn\'t me.')
        # For regular visitors, just group them by cookie. 1 user = 1 cookie.
        if cookie is not None and cookie in users_by_cookie:
          logging.debug('    But we\'ve seen this cookie ({}) before. Using existing User..'.format(cookie))
          user = users_by_cookie[cookie]
        elif label != '' and label in users_by_label:
          logging.debug('    But we\'ve seen this label ({}) before. Using existing User..'.format(label))
          user = users_by_label[label]
        else:
          logging.debug('    We haven\'t seen this cookie or label before. Creating a new User..')
          user = traffic.models.User(label=label)
          user.save()
          if cookie is not None:
            users_by_cookie[cookie] = user
          if label != '':
            users_by_label[label] = user
      visitor = traffic.models.Visitor(ip=row['ip'],
                                       cookie1=row['cookie'],
                                       user=user,
                                       label=label,
                                       user_agent=row['user_agent'])
      visitor.save()
      visitor_ids[visitor_id] = visitor
    scheme, host, path, query_str = parse_page(row['page'])
    if save:
      visit = traffic.models.Visit(
        timestamp=datetime.fromtimestamp(row['unix_time'], tz=pytz.utc),  # default timezone: UTC
        scheme=scheme,
        host=host,
        path=path,
        query_str=query_str,
        referrer=row['referrer'],
        visitor=visitor
      )
      visit.save()


def parse_page(page):
  if page is None:
    return '', '', '', ''
  # Some pages are definitely missing the "http://". None seem to be missing the domain, though.
  if page.startswith('http://') or page.startswith('https://'):
    has_scheme = True
  else:
    has_scheme = False
    page = 'http://' + page
  scheme, host, path, params, query_str, frag = urllib.parse.urlparse(page)
  if not has_scheme:
    scheme = ''
  return scheme, host, path, query_str


def print_traffic_row(row):
  output = []
  for key in ('visit_id', 'visitor_id', 'page', 'user_agent', 'is_me', 'cookie', 'label',
              'referrer', 'unix_time', 'ip'):
    output.append(row[key])
  print(*output, sep='\t')


def transfer_notepad(cursor, save=False, limit=None, resume=None, get_note=None, get_unicode=False):
  import notepad.models
  logging.info('Called transfer_notepad(cursor, limit={}, resume={}, get_note={}, get_unicode={})'
               .format(limit, resume, get_note, get_unicode))

  query = 'SELECT note_id, page, content FROM notepad ORDER BY note_id'
  total = cursor.execute(query)
  logging.info('Total notes found: '+str(total))

  pages = {}
  rows = 0
  for row in cursor.fetchall():

    rows += 1
    if limit and rows > limit:
      logging.warn('Breaking after {} rows.'.format(rows))
      break

    note_id = row['note_id']

    if resume:
      if note_id < resume:
        continue

    if get_note:
      if note_id == get_note:
        print('{note_id}:{page}\t{content}'.format(**row))
      continue

    # print('{}/{}: {}'.format(row['note_id'], row['page'], repr(row['content'])))
    # print('{note_id:2d}/{page}:\t{}'.format(repr(row['content'][:80]), **row))
    if get_unicode:
      for char in row['content']:
        if ord(char) > 127:
          print('{note_id:4d}\t{page}:\n{content}'.format(**row))
          # print('{note_id}\t{page}'.format(**row))
          break
      continue

    page_name = row['page']
    logging.info('Adding note {note_id} on page {}: {}'.format(page_name, repr(row['content']), **row))

    if page_name in pages:
      page = pages[page_name]
    elif save:
      page = notepad.models.Page(
        name=page_name
      )
      page.save()
      pages[page_name] = page

    if save:
      note = notepad.models.Note(
        page=page,
        deleted=False,
        content=row['content'],
      )
      note.save()


def tone_down_logger():
  """Change the logging level names from all-caps to capitalized lowercase.
  E.g. "WARNING" -> "Warning" (turn down the volume a bit in your log files)"""
  for level in (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG):
    level_name = logging.getLevelName(level)
    logging.addLevelName(level, level_name.capitalize())


def fail(message):
  logging.critical(message)
  sys.exit(1)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except IOError as ioe:
    if ioe.errno != errno.EPIPE:
      raise
