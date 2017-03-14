from django.test import TestCase

# Create your tests here.

"""
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