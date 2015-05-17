#!/usr/bin/env python
from __future__ import division
import re
import os
import sys
import time
import datetime
import argparse
import requests
import subprocess
import ConfigParser
import distutils.spawn
import email.mime.text

CONFIG_FILE = 'functional.cfg'
EXPIRATION_DEFAULT = 24*60*60

OPT_DEFAULTS = {}
USAGE = "%(prog)s [options]"
DESCRIPTION = """"""

def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**OPT_DEFAULTS)

  parser.add_argument('config', metavar='functional.cfg', nargs='?',
    help='Config file.')
  parser.add_argument('-s', '--status')
  parser.add_argument('-e', '--email',
    help='On test failure, send an email to this address (overrides value in config file).')
  parser.add_argument('-E', '--no-email', action='store_true',
    help='Do not send any email.')

  args = parser.parse_args(argv[1:])

  if args.config:
    config = args.config
  else:
    script_dir = os.path.relpath(os.path.dirname(os.path.realpath(__file__)))
    config = os.path.join(script_dir, CONFIG_FILE)

  settings = read_config_section(config, 'settings')

  if args.status:
    status_file = args.status
  elif hasattr(settings, 'status'):
    status_file = settings.status
  else:
    raise TesterError('A status file is required.')
  status_path = os.path.join(os.path.dirname(config), status_file)
  if not os.path.isdir(os.path.dirname(status_path)):
    raise TesterError('Directory for status file "{}" does not exist.'.format(status_path))

  expiration = EXPIRATION_DEFAULT
  if hasattr(settings, 'expiration'):
    expiration = settings.expiration

  headers = {'host': settings.hostname,
             'user-agent': settings.useragent,
             'cookie': 'visitors_v1='+settings.cookie}

  tests = get_enabled_tests(config)
  functions = globals()

  failed_tests = []
  for test in tests:
    if test not in functions:
      raise TesterError('Test "{}" from config "{}" has no test defined.'.format(test, config))
    sys.stdout.write('\t{}: '.format(test))
    result = functions[test](settings, headers)
    if 'success' in result:
      print 'success'
    else:
      failed_tests.append(test)
      print 'FAIL'
      print result['message']
      if 'mismatch' in result:
        print 'Response:'
        print result['body']

  change = check_status(status_path, len(failed_tests), expiration=expiration)
  write_status(status_path, len(failed_tests))
  if change:
    sys.stderr.write('Emailing result..\n')
    email_result(settings, failed_tests)


def read_config_section(config_path, section):
  """Read all the options from a config file section into a dict."""
  options = argparse.Namespace()
  config = ConfigParser.RawConfigParser()
  config.read(config_path)
  for key in config.options(section):
    setattr(options, key, config.get(section, key))
  if hasattr(options, '_path'):
    raise TesterError('Key conflict: "_path" exists in section "{}" of {}'
                      .format(section, config_path))
  else:
    setattr(options, '_path', config_path)
  return options


def get_enabled_tests(config_path):
  config = ConfigParser.RawConfigParser()
  config.read(config_path)
  tests = []
  for test in config.options('enabled'):
    if config.get('enabled', test).lower() == 'true':
      tests.append(test)
  return tests


def email_result(settings, failed_tests):
  from_ = '{user}@{host}'.format(user=settings.from_user, host=settings.hostname)
  to = settings.to_email
  if len(failed_tests) == 0:
    subject = 'All tests succeeded on {host}'.format(host=settings.hostname)
    body = 'Test functionality restored.'
  else:
    subject = '{total} FAILED tests on {host}'.format(total=len(failed_tests), host=settings.hostname)
    body = 'Failed tests:\n' + '\n'.join(failed_tests) + '\n'
  sendmail(from_, to, subject, body)


def sendmail(from_, to, subject, body):
  if not distutils.spawn.find_executable('sendmail'):
    return False
  message = email.mime.text.MIMEText(body)
  message['From'] = from_
  message['To'] = to
  message['Subject'] = subject
  process = subprocess.Popen(['sendmail', '-oi', '-t'], stdin=subprocess.PIPE)
  process.communicate(input=message.as_string())
  return True


def check_status(status_path, failed, expiration=EXPIRATION_DEFAULT):
  """Return True if the last status is different or too old, False if not, and None on error.
  Also returns True if the status file is nonexistent."""
  if not os.path.exists(status_path):
    return True
  with open(status_path) as status:
    status_line = status.readline()
  if not status_line:
    return
  fields = status_line.rstrip('\r\n').split('\t')
  if len(fields) < 2:
    return
  try:
    last = int(fields[0])
    last_failed = int(fields[1])
  except ValueError:
    return
  now = int(time.time())
  if failed != last_failed:
    return True
  if now - last > expiration:
    return True
  return False


def write_status(status_path, failed):
  with open(status_path, 'w') as status:
    status.write('{timestamp}\t{failed}\n'.format(timestamp=int(time.time()), failed=failed))


#################### TESTS ####################


def userinfo(settings, headers):
  data = read_config_section(settings._path, 'data_userinfo')
  headers['referer'] = data.referer
  try:
    response = requests.get('http://'+settings.hostname+data.path, headers=headers)
  except requests.exceptions.RequestException as exception:
    return {'message':'RequestException: '+str(exception)}
  if response.status_code != 200:
    return {'message':'Status '+str(response.status_code), 'body':response.text}
  result = {'message':'Incorrect response.', 'body':response.text, 'mismatch':True}
  lines = response.text.splitlines()
  if len(lines) != 4:
    return result
  if not re.search('^your IP address: [a-fA-F\d:.]+$', lines[0]):
    return result
  if lines[1] != 'referrer: '+data.referer:
    return result
  if lines[2] != 'cookie: '+settings.cookie:
    return result
  if lines[3] != 'user-agent string: '+settings.useragent:
    return result
  del(result['mismatch'])
  result['success'] = True
  return result


class TesterError(Exception):
  def __init__(self, message=None):
    if message:
      Exception.__init__(self, message)


if __name__ == '__main__':
  sys.exit(main(sys.argv))
