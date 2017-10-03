from django.conf import settings
from .models import Robot
import os
import logging
import collections
log = logging.getLogger(__name__)

DEFAULT_ROBOTS_CONFIG_PATH = os.path.join(settings.CONFIG_DIR, 'robots.yaml')

SCORES = {
  'ua_exact':1000,
  'ua_contains':500,
  'empty':200,
  'bad_host':100,
  'bot_in_ua':20,
  'sent_cookies':-100,
}


def load_bot_strings(robots_config_path=DEFAULT_ROBOTS_CONFIG_PATH):
  empty_strings = {'user_agent': collections.defaultdict(list)}
  try:
    import yaml
  except ImportError:
    log.warning('ImportError for "yaml".')
    return empty_strings
  try:
    with open(robots_config_path) as robots_config_file:
      bot_strings = yaml.safe_load(robots_config_file)
  except OSError as error:
    log.warning('OSError on trying to read {}: {}'.format(robots_config_path, error))
    return empty_strings
  return bot_strings


def is_robot(visit, thres=99, bot_strings=load_bot_strings()):
  bot_score = get_bot_score(visit.path,
                            visit.host,
                            visit.query_str,
                            visit.referrer,
                            visit.visitor.user_agent,
                            visit.visitor.cookie1,
                            visit.visitor.cookie2,
                            bot_strings=bot_strings)
  return bot_score > thres


def get_bot_score(path='', host='', query_str='', referrer='', user_agent='', cookie1='', cookie2='',
                  bot_strings=load_bot_strings(), **kwargs):
  # Highest score: Its full user_agent is in the list of known robots.
  if Robot.objects.filter(user_agent=user_agent, ip=None, cookie1=None, cookie2=None):
    return SCORES['ua_exact']
  # 2nd highest score: Its user_agent includes strings of known bots in certain places.
  if is_robot_ua(bot_strings, user_agent):
    return SCORES['ua_contains']
  # 3rd highest score: All the request fields are empty (but maybe with a path of "/").
  all_fields_empty = not (host or query_str or referrer or user_agent or cookie1 or cookie2)
  path_is_default = (path == '/' or path == '')
  if all_fields_empty and path_is_default:
    return SCORES['empty']
  # 4th highest score: If the HOST field it provided isn't one of ours.
  if invalid_host(host):
    return SCORES['bad_host']
  # 5th highest score: If "bot" appears anywhere in the user_agent.
  if 'bot' in user_agent.lower():
    return SCORES['bot_in_ua']
  # 1st negative score: It actually sent cookies. Probably a repeat visitor.
  if cookie1 or cookie2:
    return SCORES['sent_cookies']
  # Default: 0
  return 0


def invalid_host(host):
  """In the visitor's HTTP request, did it provide a HOST which isn't ours?
  Check every level of subdomains to allow things like "www.nstoler.com" to match "nstoler.com"."""
  domain = ''
  for subdomain in reversed(host.split('.')):
    if domain:
      domain = subdomain + '.' + domain
    else:
      domain = subdomain
    if domain in settings.ALLOWED_HOSTS:
      return False
  return True


def is_robot_ua(bot_strings, user_agent):
  ua_strings = bot_strings['user_agent']
  if user_agent is None or user_agent == '':
    return True
  # Does the user_agent contain a known bot name in the standard position?
  ua_halves = user_agent.split('compatible; ')
  if len(ua_halves) >= 2:
    # Look for it after 'compatible; ' and before '/', ';', or whitespace.
    bot_name = ua_halves[1].split('/')[0].split(';')[0]
    if bot_name in ua_strings['names']:
      return True
    # Check for bot names that contain whitespace (same as above, but don't split on whitespace)
    bot_name = bot_name.split()[0]
    if bot_name in ua_strings['space_delim']:
      return True
  # Does the user_agent start with a known bot name?
  fields = user_agent.split('/')
  if fields[0] in ua_strings['startswith']:
    return True
  # Does the 2nd space-delimited word match a known bot name?
  fields = user_agent.split()
  if len(fields) > 1 and fields[1] in ua_strings['2nd_word']:
    return True
  # It's not a known bot.
  return False
