from django.conf import settings
from .models import Robot, Visitor, Visit, Spam
import os
import logging
import collections
log = logging.getLogger(__name__)
try:
  import yaml
except ImportError:
  log.warning('ImportError for module "yaml".')
  yaml = None

DEFAULT_ROBOTS_CONFIG_PATH = os.path.join(settings.CONFIG_DIR, 'robots.yaml')

SCORES = {
  'ua+referrer': 1500,
  'ua_exact':1000,
  'referrer_exact':800,
  'ua_contains':500,
  'empty':200,
  'bad_host':100,
  'bot_in_ua':20,
  'mozilla_ua':-50,
  'sent_cookies':-100,
}


########## CAPTCHA ##########

#TODO: Use process_template_response to inject the HONEYPOT_NAME into response contexts, instead
#      of hardcoding it in brunner.tmpl:
#      https://stackoverflow.com/questions/5334176/help-with-process-template-response-django-middleware
CAPTCHA_VERSION = 3
HONEYPOT_NAME = 'website'
WINNING_GRIDS = (
  {1, 2, 3}, {4, 5, 6}, {7, 8, 9}, {1, 4, 7}, {2, 5, 8}, {3, 6, 9}, {1, 5, 9}, {3, 5, 7}
)

def is_bot_request(request, content_key='content'):
  params = request.POST
  is_bot = False
  if filled_honeypot(params):
    is_bot = True
  elif not solved_grid(params):
    is_bot = True
  if is_bot:
    return log_spammer(request, params.get(content_key))
  else:
    return False


def filled_honeypot(params):
  if HONEYPOT_NAME in params:
    honey_value = params.get(HONEYPOT_NAME)
    if honey_value is None:
      log.warning(f'Honeypot field {HONEYPOT_NAME!r} is None!')
      return None
    elif honey_value == '':
      return False
    else:
      return honey_value
  else:
    log.warning(f'Honeypot field {HONEYPOT_NAME!r} not included in POST!')
    return None


def solved_grid(params):
  checked_boxes = get_checked_boxes(params)
  return checked_boxes in WINNING_GRIDS


def get_checked_boxes(params):
  checked_boxes = set()
  for i in range(1, Spam.NUM_CHECKBOXES+1):
    checkbox = params.get(f'brunner:check{i}')
    if checkbox == 'on':
      checked_boxes.add(i)
  return checked_boxes


def log_spammer(request, content):
  params = request.POST
  honey_value = filled_honeypot(params)
  js_enabled_str = params.get('jsEnabled')
  if js_enabled_str == 'True':
    js_enabled = True
  elif js_enabled_str == 'False':
    js_enabled = False
  else:
    js_enabled = None
  honey_value, honey_len = truncate_field(honey_value, 1023)
  content, content_len = truncate_field(content, 2047)
  spam = Spam(
    captcha_version=CAPTCHA_VERSION,
    captcha_failed=True,
    visit=request.visit,
    honeypot_name=HONEYPOT_NAME,
    honeypot_value=honey_value,
    honeypot_len=honey_len,
    content=content,
    content_len=content_len,
    js_enabled=js_enabled,
  )
  spam.checkboxes = get_checked_boxes(params)
  spam.save()
  return spam


def truncate_field(raw_value, max_len):
  if raw_value is None or raw_value == False:
    return None, None
  value_len = len(raw_value)
  if value_len > max_len:
    value = raw_value[:max_len]
  else:
    value = raw_value
  return value, value_len


########## BOT DETECTION ##########

def read_bot_strings(robots_config_path):
  empty_strings = {'user_agent': collections.defaultdict(list)}
  if yaml is None:
    return empty_strings
  try:
    with open(robots_config_path) as robots_config_file:
      bot_strings = yaml.safe_load(robots_config_file)
    if not bot_strings or len(bot_strings.get('user_agent', ())) == 0:
      log.error('Read {}, but it appears empty.'.format(robots_config_path))
  except OSError as error:
    log.error('OSError on trying to read {}: {}'.format(robots_config_path, error))
    return empty_strings
  return bot_strings


class Classifier(object):
  def __init__(self, bot_strings=read_bot_strings(DEFAULT_ROBOTS_CONFIG_PATH)):
    self.bot_strings = bot_strings

  def reload(self, bot_strings=None):
    if bot_strings is None:
      self.bot_strings = read_bot_strings(DEFAULT_ROBOTS_CONFIG_PATH)
    else:
      self.bot_strings = bot_strings

  def is_robot(self, visit, thres=99):
    visit_data = unpack_visit(visit)
    bot_score = self.get_bot_score(**visit_data)
    return bot_score > thres

  def get_bot_score(self, path='', host='', query_str='', referrer='', user_agent='',
                    cookie1='', cookie2='', query_robots=True, **kwargs):
    # Check the user_agent and referrer against the database of known robots.
    if query_robots:
      nulls = {'ip':None, 'cookie1':None, 'cookie2':None}
      if user_agent:
        robots = Robot.objects.filter(user_agent=user_agent, **nulls)
        if robots:
          # The user_agent is in at least one Robot entry. If the entry(s) has a referrer field and
          # it matches, we have a ua+referrer match. Otherwise, the Robot(s)' referrer must be empty,
          # or we could be matching a Robot with the right user_agent but a different referrer.
          # And if both fields are specified in the Robot, both must match.
          if referrer and robots.filter(referrer=referrer):
            # Highest score: Its full user_agent and referrer are in a single Robot entry.
            return SCORES['ua+referrer']
          elif robots.filter(referrer=None):
            # 2nd highest score: Its full user_agent is in the list of known robots.
            return SCORES['ua_exact']
      if referrer:
        if Robot.objects.filter(referrer=referrer, user_agent=None, **nulls):
          # 3rd highest score: Its full referrer is in the list of known robots.
          return SCORES['referrer_exact']
    #TODO: Add match in Robot database for the path (e.g. "/wp-login.php")
    # 4th highest score: Its user_agent includes strings of known bots in certain places.
    if self.is_robot_ua(user_agent):
      return SCORES['ua_contains']
    # 5th highest score: All the request fields are empty (but maybe with a path of "/").
    all_fields_empty = not (host or query_str or referrer or user_agent or cookie1 or cookie2)
    path_is_default = (path == '/' or path == '' or path is None)
    if all_fields_empty and path_is_default:
      return SCORES['empty']
    # 6th highest score: If the HOST field it provided isn't one of ours.
    if invalid_host(host):
      return SCORES['bad_host']
    # 7th highest score: If "bot" appears anywhere in the user_agent.
    if user_agent and 'bot' in user_agent.lower():
      return SCORES['bot_in_ua']
    # 2nd lowest score: Its user_agent starts with "Mozilla/" followed by a number.
    if is_mozilla_ua(user_agent):
      # Lowest score: It also sent cookies. Possible repeat visitor.
      if cookie1 or cookie2:
        return SCORES['sent_cookies']
      else:
        return SCORES['mozilla_ua']
    #TODO: Absolute lowest score: This User has executed a totally regular interaction at least once:
    #      It made a first request, received a cookie, made a second, sending it back, and including
    #      a referrer from the same domain, etc.
    # Default: 0
    return 0

  def is_robot_ua(self, user_agent):
    ua_strings = self.bot_strings['user_agent']
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


classifier = Classifier()


def unpack_visit(visit):
  data = {
    'path': visit.path,
    'host': visit.host,
    'query_str': visit.query_str,
    'referrer': visit.referrer,
    'user_agent': visit.visitor.user_agent,
    'cookie1': '',
    'cookie2': '',
  }
  if visit.visitor.version >= 2:
    data['cookie1'] = visit.visitor.cookie1
    data['cookie2'] = visit.visitor.cookie2
  return data


def invalid_host(host):
  """In the visitor's HTTP request, did it provide a HOST which isn't ours?
  Check every level of subdomains to allow things like "www.nstoler.com" to match "nstoler.com"."""
  if host is None:
    return True
  domain = ''
  for subdomain in reversed(host.split('.')):
    if domain:
      domain = subdomain + '.' + domain
    else:
      domain = subdomain
    if domain in settings.ALLOWED_HOSTS:
      return False
  return True


def is_mozilla_ua(user_agent):
  if user_agent is None:
    return False
  first_word = user_agent.split()[0]
  fields = first_word.split('/')
  if len(fields) <= 1:
    return False
  if fields[0] != 'Mozilla':
    return False
  try:
    float(fields[1])
    return True
  except ValueError:
    return False


def mark_robot(user_agent, referrer):
  # Create a Robot for these strings.
  try:
    robot, created = Robot.objects.get_or_create(user_agent=user_agent,
                                                 referrer=referrer,
                                                 cookie1=None,
                                                 cookie2=None,
                                                 ip=None,
                                                 defaults={'version':2})
  except Robot.MultipleObjectsReturned:
    pass
  # Mark existing Visitors in database according to these new strings.
  if user_agent and referrer:
    bot_score = SCORES['ua+referrer']
    visitors = Visitor.objects.filter(user_agent=user_agent, visit__referrer=referrer,
                                      bot_score__lt=bot_score)
  elif user_agent:
    bot_score = SCORES['ua_exact']
    visitors = Visitor.objects.filter(user_agent=user_agent, bot_score__lt=bot_score)
  elif referrer:
    bot_score = SCORES['referrer_exact']
    visitors = Visitor.objects.filter(visit__referrer=referrer, bot_score__lt=bot_score)
  marked = visitors.update(bot_score=bot_score)
  return marked


def mark_all_robots(query_robots=False, start=0, end=None):
  """Go through the entire database and mark robots we weren't aware of before.
  Basically re-loads robots.yaml and marks historical bots."""
  #TODO: Cache .save()s and commit them all at once using @transaction.atomic:
  #      https://stackoverflow.com/questions/3395236/aggregating-saves-in-django/3397586#3397586
  # Re-load robots.yaml.
  if end is None:
    end = Visit.objects.count()+1
  classifier.reload()
  likely_bots = 0
  likely_humans = 0
  for visit in Visit.objects.filter(id__gte=start, id__lte=end):
    visit_data = unpack_visit(visit)
    bot_score = classifier.get_bot_score(query_robots=query_robots, **visit_data)
    prev_score = visit.visitor.bot_score
    # Set the Visitor's bot_score to the one we just determined if it hasn't been set yet, or if
    # the new score is further from zero than the previous one.
    if prev_score == 0 or abs(bot_score) > abs(prev_score):
      visit.visitor.bot_score = bot_score
      visit.visitor.save()
      if bot_score > 0:
        likely_bots += 1
      elif bot_score < 0:
        likely_humans += 1
  logging.info('Finished marking all bots. Results: {} likely bots, {} likely humans'
               .format(likely_bots, likely_humans))
  return likely_bots, likely_humans
