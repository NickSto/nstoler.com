#!/usr/bin/env python
from __future__ import division
import re
import os
import sys
import socket
import httplib
import argparse
import ConfigParser

OPT_DEFAULTS = {}
USAGE = "%(prog)s [options]"
DESCRIPTION = """"""

def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.set_defaults(**OPT_DEFAULTS)

  parser.add_argument('config', metavar='functional.cfg',
    help='Config file.')

  args = parser.parse_args(argv[1:])

  settings = read_config_section(args.config, 'settings')

  if not userinfo(settings):
    print "FAIL: userinfo"


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


def userinfo(settings):
  data = read_config_section(settings._path, 'data_userinfo')
  headers = {'Host': settings.hostname,
             'User-Agent': settings.useragent,
             'Cookie': 'visitors_v1='+settings.cookie,
             'Referer': data.referer}
  conex = httplib.HTTPConnection(settings.host)
  try:
    conex.connect()
  except (httplib.HTTPException, socket.error):
    sys.stderr.write('Connection error.\n')
    return False
  try:
    conex.request('GET', data.path, '', headers)
  except (httplib.HTTPException, socket.error):
    sys.stderr.write('Request error.\n')
    return False
  try:
    response = conex.getresponse()
  except (httplib.HTTPException, socket.error):
    sys.stderr.write('Getresponse error.\n')
    return False
  if response.status != 200:
    sys.stderr.write('Status {}.\n'.format(response.status))
    return False
  body = response.read(2048)
  conex.close()
  lines = body.splitlines()
  if len(lines) != 4:
    return False
  if not re.search('^your IP address: [a-fA-F\d:.]+$', lines[0]):
    return False
  if lines[1] != 'referrer: '+data.referer:
    return False
  if lines[2] != 'cookie: '+settings.cookie:
    return False
  if lines[3] != 'user-agent string: '+settings.useragent:
    return False
  return True


class TesterError(Exception):
  def __init__(self, message=None):
    if message:
      Exception.__init__(self, message)


if __name__ == '__main__':
  sys.exit(main(sys.argv))
