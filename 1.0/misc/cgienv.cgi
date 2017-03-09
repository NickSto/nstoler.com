#!/usr/bin/perl -w
#cgienv.cgi
#
# Prints all the CGI environment variables given by the server

########## MAIN BODY ##########

use strict;
use CGI;
use lib "$ENV{'DOCUMENT_ROOT'}/code";
use Traffic;
use Auth;

# Log the visit
add_visit_plain();

# Set up CGI DBI object
my $cgi = new CGI;

# If cookie is not authorized, print error and exit
if (! admin_cookie()) {
  print $cgi->header('text/html');
  print "Error: You are not yet authorized for this content.\n";
  exit(0);
}

print $cgi->header('text/plain');
foreach my $key (sort(keys(%ENV))) {
    print "$key = $ENV{$key}\n";
}