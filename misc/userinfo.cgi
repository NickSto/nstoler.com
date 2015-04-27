#!/usr/bin/perl -w
#userinfo.cgi
#
########## MAIN BODY ##########

# Printing to apache's error log to identify where my entries will start and
# make my "section" more visible.
print STDERR "\n$0\nSTART RUN: ", time, "\n";

use strict;
use CGI;
use CGI::Cookie;
use lib '/home/public/code';
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
