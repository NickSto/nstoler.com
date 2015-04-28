#!/usr/bin/perl -w
#cgienv.cgi
#
# Prints all the CGI environment variables given by the server

########## MAIN BODY ##########

# Printing to apache's error log to identify where my entries will start and
# make my "section" more visible.
print STDERR "\nSTART RUN: ", time, "\n\n";

use strict;
use CGI;
use lib '/home/public/code';
use Traffic;

# Log the visit
add_visit_plain();

# Set up CGI, HTML::Template, and DBI objects 
my $cgi = new CGI;

print $cgi->header('text/html');
foreach my $key (sort(keys(%ENV))) {
    print "$key = $ENV{$key}<br>\n";
}