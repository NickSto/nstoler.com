from django.conf import settings
from django.utils import timezone
from .models import IpInfo
from datetime import datetime
import pytz
import time
import logging
import urllib.parse
from utils import http_request, HttpError
log = logging.getLogger(__name__)

# http for lower latency (and we don't care that much about this kind of attack).
IPSTACK_URL = 'http://api.ipstack.com/{}?access_key={key}'
IPINFO_URL = 'http://ipinfo.io/{}'
# requires https
GOOGLE_TZ_URL = ('https://maps.googleapis.com/maps/api/timezone/json?key={key}'
                 '&location={lat},{long}&timestamp={timestamp}')
TZAPI_URL = 'https://timezoneapi.io/api/ip?ip={}'
MAX_RESPONSE = 65536
DEFAULT_TIMEOUT = 1
TTL_DEFAULT = 24*60*60  # Cache IpInfo data for 1 day.
# Possible other data source:
# https://stat.ripe.net/docs/data_api (semi-official, but ASN only)


def ip_to_ipinfo(ip, ttl=TTL_DEFAULT, timeout=DEFAULT_TIMEOUT):
  """Get the IpInfo for an ip address, checking the cache first.
  If young-enough entry exists in the local database, make a request to an API to get the info,
  store it in the local database, and return it."""
  ip_infos = IpInfo.objects.filter(ip=ip).order_by('-timestamp')
  if ip_infos:
    zone = pytz.timezone(settings.TIME_ZONE)
    now = datetime.now(tz=zone)
    ip_info = ip_infos[0]
    age = (now - ip_info.timestamp).total_seconds()
    if age < ttl:
      return ip_info
  ip_data = get_ip_data(ip, timeout=timeout)
  if ip_data:
    return make_ip_info(ip, ip_data)
  else:
    return None


def make_ip_info(ip, data):
  if not ip:
    version = None
  elif ':' in ip:
    version = 6
  else:
    version = 4
  ip_info = IpInfo(ip=ip,
                   version=version,
                   asn=data.get('asn'),
                   isp=data.get('isp', ''),
                   hostname=data.get('hostname', ''),
                   timezone=data.get('timezone', ''),
                   latitude=data.get('latitude'),
                   longitude=data.get('longitude'),
                   country=data.get('country', ''),
                   region=data.get('region', ''),
                   town=data.get('town', ''),
                   zip=data.get('zip'))
  ip_info.save()
  return ip_info


def get_ip_data(ip, timeout=DEFAULT_TIMEOUT):
  data1 = get_ipinfo_data(ip, timeout=timeout)
  return data1
  #TODO: timezoneapi.io free tier ended. Replace with a paid play for get_tz_google() or possibly
  #      get_ipstack_data().
  data2 = get_tzapi_data(ip, timeout=timeout)
  if not (data1 or data2):
    return None
  # Merge data from the two sources.
  # - data from tzapi takes precedence
  data = {}
  if data1:
    data.update(data1)
  if data2:
    data.update(data2)
  return data


def get_ipstack_data(ip, timeout=DEFAULT_TIMEOUT):
  """Get IP data from ipstack.com.
  Free limit: 10,000 requests per month (>=322 requests per day) (as of July 2018).
  Fields provided:
    timezone (with a paid plan)
    latitude
    longitude
    country
    region
    town
    zip"""
  api_key = getattr(settings, 'IPSTACK_KEY', None)
  if not api_key:
    return None
  response = get_api_data(IPSTACK_URL.format(ip, key=api_key),
                          timeout=timeout,
                          max_response=MAX_RESPONSE)
  if response is None:
    return None
  if response.get('success') == 'false':
    error_msg = dget(response, 'error', 'info')
    if error_msg:
      logging.warning('Error getting ip data from ipstack.com: "{}"'.format(error_msg))
    else:
      logging.warning('Error getting ip data from ipstack.com')
    return None
  our_data = {}
  for our_name, their_name in (('timezone', 'time_zone'),
                               ('latitude', 'latitude'),
                               ('longitude', 'longitude'),
                               ('country', 'country_name'),
                               ('region', 'region_name'),
                               ('town', 'city'),
                               ('zip', 'zip')):
    value = response.get(their_name)
    # For bogon ips like 127.0.0.1, ipstack.com gives None values.
    if value:
      our_data[our_name] = value
  try:
    our_data['zip'] = int(our_data['zip'])
  except (ValueError, KeyError):
    our_data['zip'] = None
  return our_data


def get_tzapi_data(ip, timeout=DEFAULT_TIMEOUT):
  """Get IP data from timezoneapi.io.
  Fields provided:
    country
    region
    town
    zip
    latitude
    longitude
    timezone (unique)
  Limit: No more free tier (as of Oct 4, 2018)."""
  if ip == '127.0.0.1':
    return None
  response = get_api_data(TZAPI_URL.format(ip), timeout=timeout, max_response=MAX_RESPONSE)
  if response is None:
    return None
  elif dget(response, 'meta', 'code') != '200' or 'data' not in response:
    message = dget(response, 'meta', 'message')
    if message:
      logging.warning('Error getting ip data from timezoneapi.io: "{}"'.format(message))
    else:
      logging.warning('Error getting ip data from timezoneapi.io.'.format(message))
    return None
  our_data = {}
  response_data = response['data']
  for our_name, their_name in (('country', 'country'),
                               ('region', 'state'),
                               ('town', 'city'),
                               ('zip', 'postal')):
    value = response_data.get(their_name)
    # For bogon ips like 10.1.2.3, timezoneapi.io gives "" values, and None for the objects
    # 'timezone' and 'datetime'.
    # Notably, though, for 127.0.0.1, it gives a valid response: North Pole, AK.
    if value:
      our_data[our_name] = value
  tz = dget(response_data, 'timezone', 'id')
  if tz:
    our_data['timezone'] = tz
  loc_str = response_data.get('location')
  if loc_str:
    fields = loc_str.split(',')
    if len(fields) == 2:
      try:
        our_data['latitude'] = float(fields[0])
        our_data['longitude'] = float(fields[1])
      except ValueError:
        pass
  return our_data


def get_ipinfo_data(ip, timeout=DEFAULT_TIMEOUT):
  """Get IP data from ipinfo.io.
  Fields provided:
    country (2-letter abbreviation)
    region
    town
    zip
    latitude
    longitude
    asn (unique)
    isp (unique)
    hostname (unique)
  Limit: 1000 requests per day (as of June 2018)."""
  response = get_api_data(IPINFO_URL.format(ip),
                          timeout=timeout,
                          max_response=MAX_RESPONSE)
  if response is None:
    return None
  our_data = {}
  fields = response.get('org', '').split(' ')
  if len(fields) < 2:
    pass
  else:
    asn_str = fields[0].lstrip('AS')
    try:
      our_data['asn'] = int(asn_str)
    except ValueError:
      pass
    our_data['isp'] = ' '.join(fields[1:])
  for our_name, their_name in (('hostname', 'hostname'),
                               ('country', 'country'),
                               ('town', 'city'),
                               ('region', 'region'),
                               ('zip', 'postal')):
    # For bogon ips like 127.0.0.1, ipinfo.io gives a dict containing only the keys "ip" and
    # "bogon" (True).
    try:
      our_data[our_name] = response[their_name]
    except KeyError:
      pass
  try:
    our_data['zip'] = int(our_data['zip'])
  except (ValueError, KeyError):
    our_data['zip'] = None
  try:
    fields = response['loc'].split(',')
    if len(fields) == 2:
      our_data['latitude'] = float(fields[0])
      our_data['longitude'] = float(fields[1])
  except KeyError:
    pass
  return our_data


def get_tz_google(latitude, longitude, timeout=DEFAULT_TIMEOUT):
  """Get timezone data from Google.
  As of July 2018, this requires an API key and a paid plan."""
  now = time.time()
  api_key = getattr(settings, 'GOOGLE_API_KEY', None)
  if not api_key:
    return None
  url = GOOGLE_TZ_URL.format(key=api_key, timestamp=now, latitude=latitude, longitude=longitude)
  response = get_api_data(url, timeout=timeout, max_response=MAX_RESPONSE)
  if response is None:
    return None
  elif response.get('status') != 'OK' or 'timeZoneId' not in response:
    logging.warning('Error getting ip timezone data for {}, {} from Google. '
                    'Returned error "{status}".'.format(latitude, longitude, **response))
    return None
  else:
    return response['timeZoneId']


def get_api_data(url, timeout=DEFAULT_TIMEOUT, max_response=MAX_RESPONSE):
  try:
    response = http_request(url, timeout=timeout, max_response=max_response, json=True)
    return response
  except HttpError as error:
    domain = urllib.parse.urlparse(url).netloc
    log.error('Error making request to {} API ({}): {}'
              .format(domain, error.type, error.message))
    return None


def set_timezone(request):
  """Set the timezone to the user's one and return which one that is.
  Returns the abbreviation of the timezone, like "PST".
  On failure, returns the abbrevation of `settings.TIME_ZONE`."""
  try:
    ip = request.visit.visitor.ip
  except AttributeError:
    ip = request.META.get('REMOTE_ADDR')
  ipinfo = IpInfo.objects.filter(ip=ip).order_by('-timestamp')
  if ipinfo:
    try:
      zone = pytz.timezone(ipinfo[0].timezone)
      timezone.activate(zone)
      tz = get_tz_abbrv(ipinfo[0].timezone)
    except pytz.UnknownTimeZoneError:
      log.warning('set_timezone(): pytz.UnknownTimeZoneError on "{}" (ip {})'
                  .format(ipinfo[0].timezone, ip))
      tz = None
  else:
    log.warning('set_timezone(): Could not find ip {} in database.'.format(ip))
    tz = None
  if tz:
    return tz
  else:
    try:
      return pytz.timezone(settings.TIME_ZONE)
    except pytz.UnknownTimeZoneError:
      log.warning('set_timezone(): Failed. Returning UTC.')
      return 'UTC'


def tz_convert(dt, timezone):
  """Convert a timezone-aware datetime object to a different timezone.
  `timezone` should be a string like "America/Chicago" (as returned by `get_ip_timezone()`)"""
  tz = pytz.timezone(timezone)
  return dt.astimezone(tz)


def get_tz_abbrv(timezone):
  """Give a string like "America/Chicago", get a string like "CST"."""
  if timezone is None:
    return None
  try:
    tz = pytz.timezone(timezone)
  except pytz.UnknownTimeZoneError:
    return None
  return tz.tzname(datetime.now())


def dget(this_dict, *keys):
  """Reference a value deep in a nested series of dicts.
  `dget(d, 'a', 'b', 'c')` is equivalent to `d.get('a', {}).get('b', {}).get('c')`,
  except it doesn't waste time creating all the intermediate default dicts.
  It's like saying `d['a']['b']['c']`, except that if any of the keys are missing,
  it will return None."""
  for key in keys:
    value = this_dict.get(key)
    if value is None:
      return None
    elif isinstance(value, dict):
      this_dict = value
  return value
