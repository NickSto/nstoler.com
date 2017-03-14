from django.test import TestCase

# Create your tests here.

"""
#TODO: Test the sequence of a first-time vistor arriving at a static, Nginx page, then going to a
       dynamic, Django one. Make sure the sequence of obtaining a visitors_v2, then being assigned a
       visitors_v1 is followed. Might work if I make sure to run watch_nginx.py first.
#TODO: Similarly, also test arriving at a dynamic page first, then a static one.
#TODO: Test traffic.lib.get_or_create_visitor() with these combinations:
 ip    cookie1 cookie2 user_agent
valid   valid   valid   valid
valid   valid   valid   None
valid   valid   None    valid
valid   None    valid   valid
valid   valid   None    None
valid   None    valid   None
valid   None    None    valid
valid   None    None    None
And maybe each of these combined with the database situation where there's an exact match, an
inexact (cookie) match, or no match.
"""