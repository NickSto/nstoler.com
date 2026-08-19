import ipaddress
import urllib
import socket


def is_disallowed_ip(ip_str):
  """True if `ip_str` is a private, loopback, link-local, multicast, reserved, or unspecified
  address - i.e. anything other than a normal, public internet address."""
  ip = ipaddress.ip_address(ip_str)
  return (
    ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved
    or ip.is_unspecified
  )


def check_url_is_public(url):
  """Resolve `url`'s hostname and check that none of its ip addresses are internal/private.
  Returns an error message string if it's not safe to fetch, or None if it looks fine.
  Note! This doesn't defend against DNS rebinding (where the hostname resolves to a public ip here,
  then to a private one when the request actually connects). Defending against that would require
  pinning the connection to the ip we already checked."""
  hostname = urllib.parse.urlsplit(url).hostname
  if not hostname:
    return 'Could not parse a hostname from the url.'
  try:
    addr_info = socket.getaddrinfo(hostname, None)
  except socket.gaierror as error:
    return f'Could not resolve hostname {hostname!r}: {error}'
  for family, type_, proto, canonname, sockaddr in addr_info:
    if is_disallowed_ip(sockaddr[0]):
      return f'Refusing to fetch a url that resolves to a private/internal address ({sockaddr[0]}).'
  return None