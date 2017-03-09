#!/usr/bin/perl -w
#export.cgi
=begin comment

For my Notepad web application.

Backup application: This prints all current notes in the notepad
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
my $CONFIG_SECTION = "Customizer";

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
my $notes = join('', get_notes($config));

# Print the data
print $cgi->header('text/plain');
print $notes;




#################### SUBROUTINES ####################

# Finds notes for all pages
sub get_notes {
	
	my ($config) = @_;
	
	return `mysqldump -u $$config{user} -h $$config{host} -p --password=$$config{password} --add-locks $$config{database} notepad`;

}
