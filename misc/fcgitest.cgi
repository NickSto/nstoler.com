#!/usr/bin/perl -w
# Make sure fcgiwrap is working by printing all CGI environment variables.
use strict;
use CGI;

# Create new CGI object 
my $cgi = new CGI;

print $cgi->header('text/plain');
foreach my $key (sort(keys(%ENV))) {
    print "$key = $ENV{$key}\n";
}
