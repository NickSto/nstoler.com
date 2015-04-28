#!/usr/bin/perl -w
#notes_add.cgi
#
# Adds a note from the notes.cgi page via a web form and my MySQL database


########## MAIN BODY ##########

# Printing to apache's error log to identify where my entries will start and
# make my "section" more visible.
print STDERR "\nSTART RUN: ", time, "\n\n";

use strict;
use CGI;
use HTML::Template;
use DBI;
use Config::IniFiles;
use lib "$ENV{'DOCUMENT_ROOT'}/code";
use DBIconnect;
use Passhash;
use Traffic;
	
# Log the visit
#add_visit_plain();

# Constants
my $root = $ENV{'DOCUMENT_ROOT'};
my $TMPL_FILE = "notes.tmpl";
my $CONFIG_FILE = "$root/protect/dbi_config.ini";
my $CONFIG_SECTION = "Customizer";
my $HASH_FILE = "$root/protect/auth.ini";

# Set up CGI, HTML::Template, and DBI objects 
my $cgi = new CGI;
my $tmpl = HTML::Template->new(filename => $TMPL_FILE);
my $dbh = DBI_connect($CONFIG_FILE, $CONFIG_SECTION);

# Get query from POST
my $content = $cgi->param('content');
my $auth = $cgi->param('auth');

# Check authentication
my $hash_db = Config::IniFiles->new( -file => $HASH_FILE ) or
		die "failed to read INI file $HASH_FILE: $!";
my $hash = $hash_db->val('SVH', 'main');
my $salt = $hash_db->val('SVH', 'salt');
unless (salted_vary_hash($auth, $salt) eq $hash) {
	print STDERR "incorrect password\n";
	exeunt($cgi, $dbh);
}

# Add link to MySQL
add_note($dbh, $content);

exeunt($cgi, $dbh);

sub exeunt {
	
	my ($cgi, $dbh) = @_;
	
	print $cgi->redirect('notes.cgi');
	
	# Disconnect from database
	$dbh->disconnect();
	
	exit;
}



#################### SUBROUTINES ####################

# Adds note represented by $content to the database
sub add_note {
	
	my ($dbh, $content) = @_;
	
	my $command = qq{
		INSERT IGNORE INTO notes (content)
		VALUES ( ? );
	};
	
	my $dsh = $dbh->prepare($command);
	$dsh->execute($content);
	
	$dsh->finish();
}