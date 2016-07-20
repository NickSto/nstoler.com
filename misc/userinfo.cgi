#!/usr/bin/perl -w
#userinfo.cgi
#
########## MAIN BODY ##########

use strict;
use CGI;
use CGI::Cookie;
use lib "$ENV{'DOCUMENT_ROOT'}/code";
use Traffic;

my $COOKIE_NAME = "visitors_v1";

# Log the visit
add_visit_plain();

# Set up CGI object 
my $cgi = new CGI;

my $ip = $cgi->remote_addr();
my $referrer = $cgi->referer();
my $cookie = get_cookie($COOKIE_NAME);
my $user_agent = $cgi->user_agent();

print $cgi->header('text/plain');
print "your IP address: $ip\n";
print "referrer: $referrer\n";
print "cookie: $cookie\n";
print "user-agent string: $user_agent\n";
