#!/usr/bin/perl -w
#gethash.cgi
# Allow me (or anyone) to quickly get the hash of any new password I want to
# use on my site. It will use the exact same salt & method as my authentication
# schemes.

# Printing to apache's error log to identify where my entries will start and
# make my "section" more visible.
print STDERR "\nSTART RUN: ", time, "\n\n";

use strict;
use CGI;
use Config::IniFiles;
use lib '/home/public/code';
use Passhash;
use Traffic;

# Log the visit
add_visit_plain();

# Constants
my $HASH_FILE = "/home/public/protect/auth.ini";
my $DELAY = 2; #seconds

# Set up CGI object
my $cgi = new CGI;

# Get query from POST
my $password = $cgi->param('password');
my $spambot = $cgi->param('url');

# Hash the password
my $hash_db = Config::IniFiles->new( -file => $HASH_FILE ) or
		die "failed to read INI file $HASH_FILE: $!";
my $salt = $hash_db->val('SVH', 'salt');
my $hash = salted_vary_hash($password, $salt);

# check spambot detection field
if ($spambot) {
	print $cgi->redirect('gethash.html');
	exit;
}

# pause just to make brute forcing impossible
sleep $DELAY;

# print results
print $cgi->header('text/html');
print $hash, "<br />\n";
print '<a href="gethash.html">Go back</a>'
