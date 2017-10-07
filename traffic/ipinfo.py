from django.conf import settings
from django.utils import timezone
from .models import IpInfo
from datetime import datetime
import utils
import pytz
import json
import logging
log = logging.getLogger(__name__)


FREEGEOIP_DOMAIN = 'freegeoip.net'
FREEGEOIP_PATH = '/json/{}'
IPINFO_DOMAIN = 'ipinfo.io'
IPINFO_PATH = '/{}'
TZAPI_DOMAIN = 'timezoneapi.io'  # Requires https.
TZAPI_PATH = '/api/ip?ip={}'
MAX_RESPONSE = 65536
DEFAULT_TIMEOUT = 1
TTL_DEFAULT = 24*60*60  # Cache IpInfo data for 1 day.


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
                   isp=data.get('isp'),
                   hostname=data.get('hostname'),
                   timezone=data.get('timezone'),
                   latitude=data.get('latitude'),
                   longitude=data.get('longitude'),
                   country=data.get('country'),
                   region=data.get('region'),
                   town=data.get('town'),
                   zip=data.get('zip'))
  ip_info.save()
  return ip_info


def get_ip_data(ip, timeout=DEFAULT_TIMEOUT):
  data1 = get_ipinfo_data(ip, timeout=timeout)
  data2 = get_freegeoip_data(ip, timeout=timeout)
  if not (data1 or data2):
    return None
  data = {}
  if data1:
    data.update(data1)
  if data2:
    data.update(data2)
  return data


def get_freegeoip_data(ip, timeout=DEFAULT_TIMEOUT):
  """Get IP data from freegeoip.net.
  They uniquely get us the timezone. And the country field isn't abbreviated.
  All other data is also available from ipinfo.io.
  Limit: 15,000 requests per hour (as of Oct 2017)"""
  response = get_api_data(FREEGEOIP_DOMAIN,
                          FREEGEOIP_PATH.format(ip),
                          secure=False,  # for lower latency
                          timeout=timeout,
                          max_response=MAX_RESPONSE)
  if response is None:
    return None
  our_data = {}
  for our_name, their_name in (('timezone', 'time_zone'),
                               ('latitude', 'latitude'),
                               ('longitude', 'longitude'),
                               ('country', 'country_name'),
                               ('region', 'region_name'),
                               ('town', 'city'),
                               ('zip', 'zip_code')):
    # For bogon ips like 127.0.0.1, freegeoip.net gives blank values like "" and 0.
    value = response.get(their_name)
    if value:
      our_data[our_name] = response[their_name]
  try:
    our_data['zip'] = int(our_data['zip'])
  except (ValueError, KeyError):
    pass
  return our_data


def get_ipinfo_data(ip, timeout=DEFAULT_TIMEOUT):
  """Get IP data from ipinfo.io.
  They uniquely get us the ASN, ISP, and hostname
  All other data is also available from freegeoip.net.
  Limit: 1000 requests per day (as of Oct 2017)."""
  response = get_api_data(IPINFO_DOMAIN,
                          IPINFO_PATH.format(ip),
                          secure=False,  # for lower latency
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
    pass
  try:
    fields = response['loc'].split(',')
    if len(fields) == 2:
      our_data['latitude'] = float(fields[0])
      our_data['longitude'] = float(fields[1])
  except KeyError:
    pass
  return our_data


def get_api_data(domain, path, secure=True, timeout=DEFAULT_TIMEOUT, max_response=MAX_RESPONSE):
  response = utils.http_request(domain, path, secure=secure, timeout=timeout, max_response=max_response)
  if response:
    try:
      return json.loads(response)
    except json.JSONDecodeError:
      return None
  else:
    return None


def set_timezone(request):
  """Set the timezone to the user's one and return which one that is.
  Returns the abbreviation of the timezone, like "PST".
  On failure, returns the abbrevation of settings.TIME_ZONE."""
  ipinfo = IpInfo.objects.filter(ip=request.visit.visitor.ip).order_by('-timestamp')
  if ipinfo:
    timezone.activate(pytz.timezone(ipinfo[0].timezone))
    tz = get_tz_abbrv(ipinfo[0].timezone)
  else:
    tz = None
  if tz:
    return tz
  else:
    return pytz.timezone(settings.TIME_ZONE)


def tz_convert(dt, timezone):
  """Convert a timezone-aware datetime object to a different timezone.
  "timezone" should be a string like "America/Chicago" (as returned by get_ip_timezone())"""
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
