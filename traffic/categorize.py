from django.conf import settings
import os
import logging
import collections
log = logging.getLogger(__name__)

DEFAULT_ROBOTS_CONFIG_PATH = os.path.join(settings.CONFIG_DIR, 'robots.yaml')

#TODO: The main way to filter out bots should be by marking visitors in the database with a
#      "bot_likelihood" value. Then a simple database query can filter them out. That field can be
#      set in a few ways. One should be via a UI element in the traffic monitor that lets me mark
#      all visitors with a given user agent as bots. That could set a high value for those visitors.
#      Another, more flexible way would be via the robots.yaml file. Maybe that would be a slightly
#      lower value. I should have a specific button on the traffic monitor page to load it and
#      mark bots in the database using the updated info. I could also just mark any visitor with
#      "bot" in the user_agent with a low (but positive) value.


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


def is_robot(visit, bot_strings=load_bot_strings()):
  visitor = visit.visitor
  if not (visit.host or visit.query_str or visit.referrer or visitor.user_agent or visitor.cookie1
          or visitor.cookie2) and (visit.path == '/' or visit.path == ''):
    return True
  elif invalid_host(visit.host):
    return True
  else:
    return is_robot_ua(bot_strings, visitor.user_agent)


def invalid_host(host):
  """Check every level of subdomains to allow things like "www.nstoler.com" to match "nstoler.com".
  """
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
