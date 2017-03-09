#!/usr/bin/perl -w
#export_visits.cgi
=begin comment

For my Traffic Monitor web application.

Backup application: This prints all current visits in the traffic monitor
database, using mysqldump.

=end comment
=cut

use strict;
use CGI;
use DBI;
use Config::IniFiles;
use lib "$ENV{'DOCUMENT_ROOT'}/code";
use DBIconnect;
use Traffic;
use Auth;

# Log the visit
add_visit_plain();

# Constants
my $CONFIG_FILE = "$ENV{'DOCUMENT_ROOT'}/protect/dbi_config.ini";
my $CONFIG_SECTION = "Tracker";

# Set up CGI and DBI objects 
my $cgi = new CGI;
my $config = get_config($CONFIG_FILE, $CONFIG_SECTION);

# If cookie is not authorized, print error and exit
if (! admin_cookie()) {
  print $cgi->header('text/html');
  print "Error: You are not yet authorized for this content.\n";
  exit(0);
}

# Get visits from MySQL
my $visits = join('', get_visits($config));

# Print the data
print $cgi->header('text/plain');
print $visits;




#################### SUBROUTINES ####################

# Gets mysqldump of all visits
sub get_visits {
	
	my ($config) = @_;
	
	return `mysqldump -u $$config{user} -h $$config{host} -p --password=$$config{password} --add-locks --ignore-table=traffic.accesses --ignore-table=traffic.accessors $$config{database}`;

}
