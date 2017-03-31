from django.conf import settings


##### Bot detection #####

#TODO: Put these in the database for more flexibility and possibly even a gain in speed.
# These names occur in a known location in the user_agent string: After "compatible; " and before
# "/" or ";", e.g.: Mozilla/5.0 (compatible; Exabot/3.0; +http://www.exabot.com/go/robot)
UA_BOT_NAMES = ('Googlebot', 'bingbot', 'Baiduspider', 'YandexBot', 'AhrefsBot', 'Yahoo! Slurp',
                'Exabot', 'Uptimebot', 'MJ12bot', 'Yeti', 'SeznamBot', 'DotBot', 'spbot', 'Ezooms',
                'BLEXBot', 'SiteExplorer', 'SEOkicks-Robot', 'WBSearchBot', 'SemrushBot',
                'SMTBot', 'Dataprovider.com', 'SISTRIX Crawler', 'coccocbot-web')
# These names occur after "compatible; " and before " ". It's incompatible with the above, which
# allows spaces in the names.
UA_BOT_NAMES_SPACE_DELIM = ('archive.org_bot',)
# For these, the user_agent string begins with the bot name, followed by a "/".
UA_BOT_STARTSWITH = ('curl', 'Sogou web spider', 'TurnitinBot', 'Wotbox', 'SeznamBot', 'Aboundex',
                     'msnbot-media', 'masscan')


def is_robot(visit):
  visitor = visit.visitor
  if not (visit.host or visit.query_str or visit.referrer or visitor.user_agent or visitor.cookie1
          or visitor.cookie2) and (visit.path == '/' or visit.path == ''):
    return True
  elif invalid_host(visit.host):
    return True
  else:
    return is_robot_ua(visitor.user_agent)


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


def is_robot_ua(user_agent):
  if user_agent is None or user_agent == '':
    return True
  # Does the user_agent contain a known bot name in the standard position?
  ua_halves = user_agent.split('compatible; ')
  if len(ua_halves) >= 2:
    # Look for it after 'compatible; ' and before '/', ';', or whitespace.
    bot_name = ua_halves[1].split('/')[0].split(';')[0]
    if bot_name in UA_BOT_NAMES:
      return True
    # Check for bot names that contain whitespace (same as above, but don't split on whitespace)
    bot_name = bot_name.split()[0]
    if bot_name in UA_BOT_NAMES_SPACE_DELIM:
      return True
  # Does the user_agent start with a known bot name?
  fields = user_agent.split('/')
  if fields[0] in UA_BOT_STARTSWITH:
    return True
  # It's not a known bot.
  return False
