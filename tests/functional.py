#!/usr/bin/env python
from __future__ import division
import re
import os
import sys
import argparse
import requests
import subprocess
import ConfigParser
import distutils.spawn

CONFIG_FILE = 'functional.cfg'

OPT_DEFAULTS = {}
USAGE = "%(prog)s [options]"
DESCRIPTION = """"""

def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**OPT_DEFAULTS)

  parser.add_argument('config', metavar='functional.cfg', nargs='?',
    help='Config file.')
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

  headers = {'host': settings.hostname,
             'user-agent': settings.useragent,
             'cookie': 'visitors_v1='+settings.cookie}

  sys.stdout.write('\tuserinfo: ')
  result = userinfo(settings, headers)
  if 'success' in result:
    print 'success'
  else:
    print 'FAIL'
    print result['message']
    if 'mismatch' in result:
      print 'Response:'
      print result['body']


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


def sendmail(settings, failed_tests):
  if not distutils.spawn.find_executable('sendmail'):
    return False
  email = """\
From: {user}@{host}
To: {email}
Subject: {total} FAILED tests on {host}

Failed tests:
{test_names}
""".format(user=settings.from_user, host=settings.hostname, email=settings.to_email,
           total=len(failed_tests), '\n'.join(failed_tests))
  process = subprocess.Popen(['sendmail', '-oi', '-t'], stdin=subprocess.PIPE)
  process.communicate(input=email)
  return True


##### TESTS #####


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
